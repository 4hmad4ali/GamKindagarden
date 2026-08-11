from django.db import migrations, models
import django.db.models.deletion


def link_completed_payments(apps, schema_editor):
    StudentPayment = apps.get_model('core', 'StudentPayment')
    Transaction = apps.get_model('core', 'Transaction')

    for payment in StudentPayment.objects.filter(status='completed').select_related('student'):
        transaction, _ = Transaction.objects.get_or_create(
            transaction_id=f'FEE-{payment.pk:08d}',
            defaults={
                'transaction_type': 'income',
                'amount': payment.paid_amount,
                'transaction_date': payment.created_date,
                'description': f'Student fee: {payment.student.first_name} {payment.student.last_name} — {payment.payment_type} ({payment.month}/{payment.year})',
                'category': 'Student fee',
                'status': 'completed',
                'student_id': payment.student_id,
            },
        )
        payment.transaction_id = transaction.pk
        payment.save(update_fields=['transaction'])


class Migration(migrations.Migration):
    dependencies = [('core', '0003_alter_medical_checkup_date')]

    operations = [
        migrations.AddField(
            model_name='studentpayment',
            name='transaction',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='student_payment', to='core.transaction'),
        ),
        migrations.RunPython(link_completed_payments, migrations.RunPython.noop),
    ]
