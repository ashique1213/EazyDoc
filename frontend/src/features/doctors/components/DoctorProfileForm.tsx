import React, { useState, useEffect } from "react";
import axios from "axios";
import { AlertCircle, CheckCircle2, Loader2, User as UserIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { Doctor, DoctorProfilePayload } from "../types";
import { useCreateDoctorProfile, useUpdateDoctorProfile, useSpecializations } from "../hooks";

interface DoctorProfileFormProps {
  initialDoctor?: Doctor | null;
  onSuccess?: (doctor: Doctor) => void;
}

export const DoctorProfileForm: React.FC<DoctorProfileFormProps> = ({
  initialDoctor,
  onSuccess,
}) => {
  const isEditing = Boolean(initialDoctor);

  const [formData, setFormData] = useState<DoctorProfilePayload>({
    full_name: initialDoctor?.full_name || "",
    registration_number: initialDoctor?.registration_number || "",
    registration_council: initialDoctor?.registration_council || "",
    registration_state: initialDoctor?.registration_state || "",
    specialization: initialDoctor?.specialization || "",
    qualifications: initialDoctor?.qualifications || "",
    years_of_experience: initialDoctor?.years_of_experience ?? 0,
    bio: initialDoctor?.bio || "",
    languages: initialDoctor?.languages || "English, Hindi",
    profile_photo: null,
  });

  const [photoPreview, setPhotoPreview] = useState<string | null>(
    initialDoctor?.profile_photo || null
  );
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const createMutation = useCreateDoctorProfile();
  const updateMutation = useUpdateDoctorProfile();
  const { data: specializations } = useSpecializations();

  useEffect(() => {
    if (initialDoctor) {
      setFormData({
        full_name: initialDoctor.full_name || "",
        registration_number: initialDoctor.registration_number || "",
        registration_council: initialDoctor.registration_council || "",
        registration_state: initialDoctor.registration_state || "",
        specialization: initialDoctor.specialization || "",
        qualifications: initialDoctor.qualifications || "",
        years_of_experience: initialDoctor.years_of_experience ?? 0,
        bio: initialDoctor.bio || "",
        languages: initialDoctor.languages || "English, Hindi",
        profile_photo: null,
      });
      setPhotoPreview(initialDoctor.profile_photo || null);
    }
  }, [initialDoctor]);

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    if (!formData.full_name.trim()) errors.full_name = "Full name is required.";
    if (!formData.registration_number.trim())
      errors.registration_number = "Registration number is required.";
    if (!formData.registration_council.trim())
      errors.registration_council = "Registration council is required.";
    if (!formData.specialization.trim()) errors.specialization = "Specialization is required.";
    if (!formData.qualifications.trim()) errors.qualifications = "Qualifications are required.";
    if ((formData.years_of_experience ?? 0) < 0)
      errors.years_of_experience = "Experience cannot be negative.";

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 2 * 1024 * 1024) {
        setFormErrors((prev) => ({
          ...prev,
          profile_photo: "Profile photo must be smaller than 2MB.",
        }));
        return;
      }
      setFormData((prev) => ({ ...prev, profile_photo: file }));
      const reader = new FileReader();
      reader.onloadend = () => {
        setPhotoPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError(null);
    setSuccessMessage(null);

    if (!validate()) return;

    try {
      if (isEditing) {
        const result = await updateMutation.mutateAsync(formData);
        setSuccessMessage("Profile updated successfully!");
        onSuccess?.(result);
      } else {
        const result = await createMutation.mutateAsync(formData);
        setSuccessMessage("Doctor profile created successfully!");
        onSuccess?.(result);
      }
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        const respData = err.response?.data as
          | { errors?: Record<string, string | string[]>; message?: string }
          | undefined;
        if (respData?.errors) {
          const fieldErrors: Record<string, string> = {};
          Object.entries(respData.errors).forEach(([key, val]) => {
            fieldErrors[key] = Array.isArray(val) ? val.join(" ") : String(val);
          });
          setFormErrors(fieldErrors);
        } else if (respData?.message) {
          setServerError(respData.message);
        } else {
          setServerError("Failed to save profile. Please check the form and try again.");
        }
      } else {
        setServerError("Failed to save profile. Please check the form and try again.");
      }
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle className="text-xl">
          {isEditing ? "Manage Practitioner Profile" : "Create Practitioner Profile"}
        </CardTitle>
        <CardDescription>
          Provide your official medical registration identity and clinical credentials.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {serverError && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Submission Error</AlertTitle>
            <AlertDescription>{serverError}</AlertDescription>
          </Alert>
        )}

        {successMessage && (
          <Alert className="mb-6 border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:text-emerald-300">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <AlertTitle>Success</AlertTitle>
            <AlertDescription>{successMessage}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Photo and Identity */}
          <div className="flex flex-col sm:flex-row items-center gap-6 pb-4 border-b">
            <div className="relative h-24 w-24 shrink-0 rounded-full border-2 border-dashed border-muted-foreground/30 flex items-center justify-center bg-muted/30 overflow-hidden">
              {photoPreview ? (
                <img
                  src={photoPreview}
                  alt="Doctor avatar"
                  className="h-full w-full object-cover"
                />
              ) : (
                <UserIcon className="h-10 w-10 text-muted-foreground" />
              )}
            </div>
            <div className="flex-1 space-y-2">
              <Label htmlFor="profile_photo">Profile Photo</Label>
              <div className="flex items-center gap-3">
                <Input
                  id="profile_photo"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handlePhotoChange}
                  className="max-w-xs text-xs file:mr-2 file:py-1 file:px-2 file:rounded-md file:border-0 file:text-xs file:bg-primary file:text-primary-foreground"
                />
                <span className="text-xs text-muted-foreground">Max 2MB (JPG, PNG, WebP)</span>
              </div>
              {formErrors.profile_photo && (
                <p className="text-xs text-destructive">{formErrors.profile_photo}</p>
              )}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {/* Full Name */}
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="full_name">
                Full Legal Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="full_name"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                placeholder="Dr. Anita Desai"
              />
              {formErrors.full_name && (
                <p className="text-xs text-destructive">{formErrors.full_name}</p>
              )}
            </div>

            {/* Medical Registration Number */}
            <div className="space-y-1.5">
              <Label htmlFor="registration_number">
                Registration Number <span className="text-destructive">*</span>
              </Label>
              <Input
                id="registration_number"
                value={formData.registration_number}
                onChange={(e) =>
                  setFormData({ ...formData, registration_number: e.target.value })
                }
                placeholder="e.g. MMC-123456"
              />
              {formErrors.registration_number && (
                <p className="text-xs text-destructive">{formErrors.registration_number}</p>
              )}
            </div>

            {/* Registration Council */}
            <div className="space-y-1.5">
              <Label htmlFor="registration_council">
                Registration Council / Authority <span className="text-destructive">*</span>
              </Label>
              <Input
                id="registration_council"
                value={formData.registration_council}
                onChange={(e) =>
                  setFormData({ ...formData, registration_council: e.target.value })
                }
                placeholder="e.g. Maharashtra Medical Council"
              />
              {formErrors.registration_council && (
                <p className="text-xs text-destructive">{formErrors.registration_council}</p>
              )}
            </div>

            {/* Registration State */}
            <div className="space-y-1.5">
              <Label htmlFor="registration_state">State / Jurisdiction</Label>
              <Input
                id="registration_state"
                value={formData.registration_state}
                onChange={(e) => setFormData({ ...formData, registration_state: e.target.value })}
                placeholder="e.g. Maharashtra"
              />
            </div>

            {/* Specialization */}
            <div className="space-y-1.5">
              <Label htmlFor="specialization">
                Specialization <span className="text-destructive">*</span>
              </Label>
              <div className="flex gap-2">
                <Input
                  id="specialization"
                  value={formData.specialization}
                  onChange={(e) => setFormData({ ...formData, specialization: e.target.value })}
                  placeholder="e.g. Cardiology"
                  list="specializations-list"
                />
                {specializations && (
                  <datalist id="specializations-list">
                    {specializations.map((spec) => (
                      <option key={spec.id} value={spec.name} />
                    ))}
                  </datalist>
                )}
              </div>
              {formErrors.specialization && (
                <p className="text-xs text-destructive">{formErrors.specialization}</p>
              )}
            </div>

            {/* Qualifications */}
            <div className="space-y-1.5">
              <Label htmlFor="qualifications">
                Qualifications <span className="text-destructive">*</span>
              </Label>
              <Input
                id="qualifications"
                value={formData.qualifications}
                onChange={(e) => setFormData({ ...formData, qualifications: e.target.value })}
                placeholder="e.g. MBBS, MD (General Medicine)"
              />
              {formErrors.qualifications && (
                <p className="text-xs text-destructive">{formErrors.qualifications}</p>
              )}
            </div>

            {/* Experience */}
            <div className="space-y-1.5">
              <Label htmlFor="years_of_experience">Years of Experience</Label>
              <Input
                id="years_of_experience"
                type="number"
                min="0"
                value={formData.years_of_experience ?? 0}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    years_of_experience: parseInt(e.target.value) || 0,
                  })
                }
              />
              {formErrors.years_of_experience && (
                <p className="text-xs text-destructive">{formErrors.years_of_experience}</p>
              )}
            </div>

            {/* Languages */}
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="languages">Languages Spoken</Label>
              <Input
                id="languages"
                value={formData.languages}
                onChange={(e) => setFormData({ ...formData, languages: e.target.value })}
                placeholder="e.g. English, Hindi, Kannada"
              />
            </div>

            {/* Biography */}
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="bio">Professional Biography</Label>
              <Textarea
                id="bio"
                rows={3}
                value={formData.bio}
                onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                placeholder="Briefly describe your clinical focus, background, and patient care philosophy..."
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button type="submit" disabled={isPending}>
              {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isEditing ? "Save Changes" : "Create Profile"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};
