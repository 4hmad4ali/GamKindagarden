import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from .models import ChatUserProfile, DirectMessage
from accounts.roles import dashboard_for_user


# ══════════════════════════════════════════════
# HELPER
# ══════════════════════════════════════════════

def get_or_create_profile(user):
    profile, _ = ChatUserProfile.objects.get_or_create(user=user)
    return profile


# ══════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════

def signup(request):
    if request.user.is_authenticated:
        return redirect(dashboard_for_user(request.user))

    error = ''
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip().lower()
        password   = request.POST.get('password', '')
        picture    = request.FILES.get('profile_picture')

        if not first_name or not email or not password:
            error = 'Please fill in all required fields.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters.'
        elif User.objects.filter(email=email).exists():
            error = 'This email is already registered.'
        else:
            # Unique username
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            profile = get_or_create_profile(user)
            if picture:
                profile.profile_picture = picture
                profile.save()

            return redirect('login_chat')

    return render(request, 'signup.html', {'error': error})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(dashboard_for_user(request.user))

    error = ''
    if request.method == 'POST':
        email        = request.POST.get('email', '').strip().lower()
        password     = request.POST.get('password', '')
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)

            if user is not None:
                login(request, user)
                # Mark online
                profile = get_or_create_profile(user)
                profile.is_online = True
                profile.save()

                # The destination is derived from server-side privileges only.
                return redirect(dashboard_for_user(user))
            else:
                error = 'Incorrect password.'
        except User.DoesNotExist:
            error = 'No account found with this email.'

    return render(request, 'login_chat.html', {'error': error})


def logout_view(request):
    if request.user.is_authenticated:
        try:
            p = request.user.chat_profile
            p.is_online = False
            p.save()
        except Exception:
            pass
    logout(request)
    return redirect('login_chat')


# ══════════════════════════════════════════════
# CHAT DASHBOARD
# ══════════════════════════════════════════════

@login_required(login_url='login_chat')
def chat_dashboard(request):
    me = request.user
    my_profile = get_or_create_profile(me)
    my_profile.is_online = True
    my_profile.save()

    all_users = list(
        User.objects.exclude(id=me.id).select_related('chat_profile').order_by('first_name', 'last_name', 'username')
    )
    user_ids = [user.id for user in all_users]
    recent_messages = DirectMessage.objects.filter(
        Q(sender=me, receiver_id__in=user_ids) | Q(receiver=me, sender_id__in=user_ids)
    ).order_by('-created_at')
    latest_by_contact = {}
    for message in recent_messages:
        contact_id = message.receiver_id if message.sender_id == me.id else message.sender_id
        latest_by_contact.setdefault(contact_id, message)
    unread_by_sender = {
        row['sender_id']: row['count'] for row in DirectMessage.objects.filter(
            receiver=me, is_read=False
        ).values('sender_id').annotate(count=Count('id'))
    }

    contacts = []
    for u in all_users:
        # Some accounts predate the chat feature and have no profile yet.
        # Create it here instead of allowing a missing related record to break
        # the chat page for every user.
        contact_profile = get_or_create_profile(u)
        pic = contact_profile.profile_picture.url if contact_profile.profile_picture else None
        online = contact_profile.is_online
        last_msg = latest_by_contact.get(u.id)
        unread = unread_by_sender.get(u.id, 0)

        contacts.append({
            'user':     u,
            'name':     u.get_full_name() or u.username,
            'picture':  pic,
            'online':   online,
            'last_msg': last_msg.content[:40] if last_msg else '',
            'last_time': last_msg.created_at.strftime('%H:%M') if last_msg else '',
            'unread':   unread,
        })

    # Online first, then by name
    contacts.sort(key=lambda x: (not x['online'], x['name']))

    my_pic = my_profile.profile_picture.url if my_profile.profile_picture else None

    context = {
        'me':         me,
        'my_name':    me.get_full_name() or me.username,
        'my_picture': my_pic,
        'contacts':   contacts,
        'dashboard_name': dashboard_for_user(me),
    }
    return render(request, 'chat_dashboard.html', context)


# ══════════════════════════════════════════════
# AJAX ENDPOINTS
# ══════════════════════════════════════════════

@login_required(login_url='login_chat')
def get_messages(request, user_id):
    """GET — بارگذاری پیام‌های مکالمه با user_id"""
    me    = request.user
    other = get_object_or_404(User, id=user_id)

    # Mark incoming as read
    DirectMessage.objects.filter(sender=other, receiver=me, is_read=False).update(is_read=True)

    msgs = DirectMessage.objects.filter(
        sender__in=[me, other],
        receiver__in=[me, other]
    ).order_by('created_at')

    data = []
    for m in msgs:
        try:
            sp  = m.sender.chat_profile
            pic = sp.profile_picture.url if sp.profile_picture else None
        except Exception:
            pic = None
        data.append({
            'id':             m.id,
            'mine':           m.sender_id == me.id,
            'text':           m.content,
            'sender_name':    m.sender.get_full_name() or m.sender.username,
            'sender_picture': pic,
            'time':           m.created_at.strftime('%H:%M'),
            'date':           m.created_at.strftime('%Y-%m-%d'),
        })

    try:
        op      = other.chat_profile
        o_pic   = op.profile_picture.url if op.profile_picture else None
        o_online = op.is_online
    except Exception:
        o_pic    = None
        o_online = False

    return JsonResponse({
        'messages':      data,
        'other_name':    other.get_full_name() or other.username,
        'other_picture': o_pic,
        'other_online':  o_online,
    })


@login_required(login_url='login_chat')
@require_POST
def send_message(request, user_id):
    """POST — ارسال پیام به user_id"""
    me    = request.user
    other = get_object_or_404(User, id=user_id)

    try:
        body    = json.loads(request.body)
        content = body.get('content', '').strip()
    except Exception:
        content = request.POST.get('content', '').strip()

    if not content:
        return JsonResponse({'ok': False, 'error': 'Empty message'})
    if len(content) > 4000:
        return JsonResponse({'ok': False, 'error': 'Message is too long.'}, status=400)
    if other.id == me.id:
        return JsonResponse({'ok': False, 'error': 'You cannot message yourself.'}, status=400)

    msg = DirectMessage.objects.create(sender=me, receiver=other, content=content)

    return JsonResponse({
        'ok':   True,
        'id':   msg.id,
        'time': msg.created_at.strftime('%H:%M'),
    })


@login_required(login_url='login_chat')
def get_unread_counts(request):
    """GET — تعداد پیام‌های خوانده‌نشده برای هر فرستنده"""
    counts = DirectMessage.objects.filter(
        receiver=request.user, is_read=False
    ).values('sender_id').annotate(count=Count('id'))

    return JsonResponse({'counts': {str(r['sender_id']): r['count'] for r in counts}})


@login_required(login_url='login_chat')
def get_online_status(request):
    """GET — وضعیت آنلاین همه کاربران"""
    users = User.objects.exclude(id=request.user.id).select_related('chat_profile')
    data = [
        {'id': user.id, 'online': getattr(user, 'chat_profile', None) and user.chat_profile.is_online}
        for user in users
    ]
    return JsonResponse({'users': data})


@login_required(login_url='login_chat')
def upload_picture(request):
    """POST — آپلود عکس پروفایل"""
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        try:
            uploaded_picture = request.FILES['profile_picture']
            if uploaded_picture.size > 5 * 1024 * 1024:
                raise ValidationError('Image must be 5 MB or smaller.')
            if uploaded_picture.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
                raise ValidationError('Only JPEG, PNG, or WebP images are allowed.')
            profile = get_or_create_profile(request.user)
            profile.profile_picture = uploaded_picture
            profile.full_clean()
            profile.save()
        except ValidationError:
            pass
    return redirect('chat_dashboard')
