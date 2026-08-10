import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import ChatUserProfile, DirectMessage


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
        return redirect('chat_dashboard')

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
        return redirect('chat_dashboard')

    error = ''
    if request.method == 'POST':
        email        = request.POST.get('email', '').strip().lower()
        password     = request.POST.get('password', '')
        account_type = request.POST.get('account_type', '')

        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)

            if user is not None:
                login(request, user)
                # Mark online
                profile = get_or_create_profile(user)
                profile.is_online = True
                profile.save()

                # Route by account type
                dest_map = {
                    'admin':   'admin_dashboard',
                    'teacher': 'teacher_dashboard',
                    'student': 'student_dashboard',
                    'doctor':  'doctor_dashboard',
                    'finance': 'finance_dashboard',
                }
                return redirect(dest_map.get(account_type, 'chat_dashboard'))
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
    profile = get_or_create_profile(me)
    profile.is_online = True
    profile.save()

    all_users = User.objects.exclude(id=me.id).order_by('first_name', 'last_name', 'username')

    contacts = []
    for u in all_users:
        try:
            up = u.chat_profile
            pic = up.profile_picture.url if up.profile_picture else None
            online = up.is_online
        except Exception:
            pic = None
            online = False

        last_msg = DirectMessage.objects.filter(
            sender__in=[me, u], receiver__in=[me, u]
        ).order_by('-created_at').first()

        unread = DirectMessage.objects.filter(
            sender=u, receiver=me, is_read=False
        ).count()

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

    my_pic = profile.profile_picture.url if profile.profile_picture else None

    context = {
        'me':         me,
        'my_name':    me.get_full_name() or me.username,
        'my_picture': my_pic,
        'contacts':   contacts,
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

    msg = DirectMessage.objects.create(sender=me, receiver=other, content=content)

    return JsonResponse({
        'ok':   True,
        'id':   msg.id,
        'time': msg.created_at.strftime('%H:%M'),
    })


@login_required(login_url='login_chat')
def get_unread_counts(request):
    """GET — تعداد پیام‌های خوانده‌نشده برای هر فرستنده"""
    from django.db.models import Count
    counts = DirectMessage.objects.filter(
        receiver=request.user, is_read=False
    ).values('sender_id').annotate(count=Count('id'))

    return JsonResponse({'counts': {str(r['sender_id']): r['count'] for r in counts}})


@login_required(login_url='login_chat')
def get_online_status(request):
    """GET — وضعیت آنلاین همه کاربران"""
    users = User.objects.exclude(id=request.user.id)
    data  = []
    for u in users:
        try:
            online = u.chat_profile.is_online
        except Exception:
            online = False
        data.append({'id': u.id, 'online': online})
    return JsonResponse({'users': data})


@login_required(login_url='login_chat')
def upload_picture(request):
    """POST — آپلود عکس پروفایل"""
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        profile = get_or_create_profile(request.user)
        profile.profile_picture = request.FILES['profile_picture']
        profile.save()
    return redirect('chat_dashboard')
