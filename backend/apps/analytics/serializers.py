from rest_framework import serializers


class AnalyticsQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(
        choices=[
            "today",
            "yesterday",
            "last_7_days",
            "last_30_days",
            "last_90_days",
            "this_month",
            "previous_month",
            "this_year",
            "custom",
        ],
        required=False,
        default="last_30_days",
    )
    date_from = serializers.DateField(required=False, allow_null=True)
    date_to = serializers.DateField(required=False, allow_null=True)
    clinic_id = serializers.UUIDField(required=False, allow_null=True)
    doctor_id = serializers.UUIDField(required=False, allow_null=True)
    status = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    refresh = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        d_from = attrs.get("date_from")
        d_to = attrs.get("date_to")
        if d_from and d_to and d_from > d_to:
            attrs["date_from"], attrs["date_to"] = d_to, d_from
        return attrs


class ClinicPerformanceQuerySerializer(AnalyticsQuerySerializer):
    search = serializers.CharField(required=False, allow_blank=True)


class DoctorPerformanceQuerySerializer(AnalyticsQuerySerializer):
    verification_status = serializers.CharField(required=False, allow_blank=True)
    search = serializers.CharField(required=False, allow_blank=True)


class ExportReportQuerySerializer(AnalyticsQuerySerializer):
    report_type = serializers.ChoiceField(
        choices=["revenue", "clinics", "doctors", "appointments", "reconciliation", "cancellations"],
        default="appointments",
    )
    format = serializers.ChoiceField(choices=["csv"], default="csv")

