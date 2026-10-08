from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class AuditLog(models.Model):
    """
    Append-only audit trail logging security and business events across tenants.
    """
    id = models.BigAutoField(primary_key=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("actor"),
    )
    clinic_id = models.UUIDField(
        _("clinic tenant id"), null=True, blank=True, db_index=True
    )
    action = models.CharField(_("action"), max_length=100, db_index=True)
    resource_type = models.CharField(_("resource type"), max_length=50, db_index=True)
    resource_id = models.CharField(_("resource id"), max_length=100, blank=True, default="")
    ip_address = models.GenericIPAddressField(_("ip address"), null=True, blank=True)
    user_agent = models.CharField(_("user agent"), max_length=500, blank=True, default="")
    details = models.JSONField(_("details"), default=dict, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("audit log")
        verbose_name_plural = _("audit logs")

    def __str__(self):
        return f"[{self.created_at}] {self.action} by {self.actor or 'Anonymous'}"
