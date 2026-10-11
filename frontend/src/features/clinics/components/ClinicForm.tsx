import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Building2, UploadCloud, Loader2, AlertCircle } from "lucide-react";
import type { Clinic, ClinicCreatePayload, ClinicUpdatePayload } from "../types";

interface ClinicFormProps {
  initialData?: Clinic;
  onSubmit: (data: ClinicCreatePayload | ClinicUpdatePayload, action: "submit" | "draft") => Promise<void>;
  isSubmitting?: boolean;
  serverErrors?: Record<string, string[] | string> | null;
  mode?: "create" | "edit";
}

export function ClinicForm({
  initialData,
  onSubmit,
  isSubmitting = false,
  serverErrors,
  mode = "create",
}: ClinicFormProps) {
  const [formData, setFormData] = useState({
    name: initialData?.name || "",
    description: initialData?.description || "",
    email: initialData?.email || "",
    phone: initialData?.phone || "",
    address_line_1: initialData?.address_line_1 || "",
    address_line_2: initialData?.address_line_2 || "",
    city: initialData?.city || "",
    state: initialData?.state || "",
    pincode: initialData?.pincode || "",
    country: initialData?.country || "India",
  });

  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(initialData?.logo || null);
  const [clientErrors, setClientErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.name.trim()) {
      errors.name = "Clinic name is required.";
    }

    if (!formData.email.trim()) {
      errors.email = "Official email address is required.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email.trim())) {
      errors.email = "Please enter a valid email address.";
    }

    if (!formData.phone.trim()) {
      errors.phone = "Phone number is required.";
    } else if (!/^\+?[0-9]{10,15}$/.test(formData.phone.trim().replace(/[\s-]/g, ""))) {
      errors.phone = "Enter a valid 10-15 digit phone number.";
    }

    if (!formData.address_line_1.trim()) {
      errors.address_line_1 = "Address line 1 is required.";
    }

    if (!formData.city.trim()) {
      errors.city = "City is required.";
    }

    if (!formData.state.trim()) {
      errors.state = "State is required.";
    }

    if (!formData.pincode.trim()) {
      errors.pincode = "Postal / PIN code is required.";
    } else if (
      formData.country.trim().toLowerCase() === "india" &&
      !/^[1-9][0-9]{5}$/.test(formData.pincode.trim())
    ) {
      errors.pincode = "Enter a valid 6-digit Indian PIN code (e.g., 560001).";
    }

    setClientErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      setClientErrors((prev) => ({
        ...prev,
        logo: "Logo file size exceeds the 2MB limit.",
      }));
      return;
    }

    const allowed = ["image/jpeg", "image/png", "image/webp"];
    if (!allowed.includes(file.type)) {
      setClientErrors((prev) => ({
        ...prev,
        logo: "Please upload a valid image (JPG, PNG, WebP).",
      }));
      return;
    }

    setClientErrors((prev) => {
      const next = { ...prev };
      delete next.logo;
      return next;
    });

    setLogoFile(file);
    const reader = new FileReader();
    reader.onloadend = () => {
      setLogoPreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = async (action: "submit" | "draft") => {
    if (!validate()) return;

    const payload: ClinicCreatePayload = {
      ...formData,
      status: action === "draft" ? "DRAFT" : "PENDING",
      logo: logoFile,
    };

    await onSubmit(payload, action);
  };

  const getFieldError = (field: string): string | undefined => {
    if (clientErrors[field]) return clientErrors[field];
    if (serverErrors && serverErrors[field]) {
      const err = serverErrors[field];
      return Array.isArray(err) ? err[0] : err;
    }
    return undefined;
  };

  return (
    <Card className="border-muted shadow-sm">
      <CardContent className="p-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit(mode === "create" ? "submit" : "draft");
          }}
          className="space-y-6"
        >
          {serverErrors && serverErrors.non_field_errors && (
            <div className="flex items-center space-x-2 rounded-lg bg-destructive/10 p-3 text-xs text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>
                {Array.isArray(serverErrors.non_field_errors)
                  ? serverErrors.non_field_errors.join(" ")
                  : serverErrors.non_field_errors}
              </span>
            </div>
          )}

          {/* Core Profile */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold tracking-wide uppercase text-muted-foreground flex items-center space-x-2">
              <Building2 className="h-4 w-4 text-primary" />
              <span>Clinic Establishment Information</span>
            </h3>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="clinic-name">Clinic Name *</Label>
                <Input
                  id="clinic-name"
                  placeholder="e.g. Apollo Speciality Healthcare"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  disabled={isSubmitting}
                />
                {getFieldError("name") && (
                  <p className="text-xs text-destructive">{getFieldError("name")}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="clinic-email">Official Contact Email *</Label>
                <Input
                  id="clinic-email"
                  type="email"
                  placeholder="reception@clinic.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  disabled={isSubmitting}
                />
                {getFieldError("email") && (
                  <p className="text-xs text-destructive">{getFieldError("email")}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="clinic-phone">Official Contact Phone *</Label>
                <Input
                  id="clinic-phone"
                  placeholder="+919876543210"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  disabled={isSubmitting}
                />
                {getFieldError("phone") && (
                  <p className="text-xs text-destructive">{getFieldError("phone")}</p>
                )}
              </div>

              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="clinic-desc">About / Specialities (Optional)</Label>
                <Textarea
                  id="clinic-desc"
                  placeholder="Describe your clinic, medical departments, and facilities..."
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  disabled={isSubmitting}
                />
              </div>
            </div>
          </div>

          {/* Location & Address */}
          <div className="space-y-4 pt-4 border-t">
            <h3 className="text-sm font-semibold tracking-wide uppercase text-muted-foreground">
              Address & Geo Details
            </h3>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="address-1">Address Line 1 *</Label>
                <Input
                  id="address-1"
                  placeholder="Building No, Street, Road"
                  value={formData.address_line_1}
                  onChange={(e) => setFormData({ ...formData, address_line_1: e.target.value })}
                  disabled={isSubmitting}
                />
                {getFieldError("address_line_1") && (
                  <p className="text-xs text-destructive">{getFieldError("address_line_1")}</p>
                )}
              </div>

              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="address-2">Address Line 2 (Optional)</Label>
                <Input
                  id="address-2"
                  placeholder="Landmark, Suite, Unit"
                  value={formData.address_line_2}
                  onChange={(e) => setFormData({ ...formData, address_line_2: e.target.value })}
                  disabled={isSubmitting}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="city">City *</Label>
                <Input
                  id="city"
                  placeholder="e.g. Bengaluru"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  disabled={isSubmitting}
                />
                {getFieldError("city") && (
                  <p className="text-xs text-destructive">{getFieldError("city")}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="state">State *</Label>
                <Input
                  id="state"
                  placeholder="e.g. Karnataka"
                  value={formData.state}
                  onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                  disabled={isSubmitting}
                />
                {getFieldError("state") && (
                  <p className="text-xs text-destructive">{getFieldError("state")}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="pincode">Postal / PIN Code *</Label>
                <Input
                  id="pincode"
                  placeholder="e.g. 560001"
                  value={formData.pincode}
                  onChange={(e) => setFormData({ ...formData, pincode: e.target.value })}
                  disabled={isSubmitting}
                />
                {getFieldError("pincode") && (
                  <p className="text-xs text-destructive">{getFieldError("pincode")}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="country">Country</Label>
                <Input
                  id="country"
                  value={formData.country}
                  onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                  disabled={isSubmitting}
                />
              </div>
            </div>
          </div>

          {/* Logo Upload */}
          <div className="space-y-4 pt-4 border-t">
            <h3 className="text-sm font-semibold tracking-wide uppercase text-muted-foreground">
              Clinic Logo (Optional)
            </h3>

            <div className="flex items-center space-x-4">
              {logoPreview ? (
                <div className="h-16 w-16 overflow-hidden rounded-xl border bg-muted flex items-center justify-center shrink-0">
                  <img
                    src={logoPreview}
                    alt="Logo Preview"
                    className="h-full w-full object-cover"
                  />
                </div>
              ) : (
                <div className="flex h-16 w-16 items-center justify-center rounded-xl border border-dashed text-muted-foreground shrink-0 bg-muted/20">
                  <UploadCloud className="h-6 w-6" />
                </div>
              )}

              <div className="space-y-1">
                <Label htmlFor="logo-upload" className="cursor-pointer text-xs font-semibold text-primary underline">
                  Choose Logo Image
                </Label>
                <p className="text-[11px] text-muted-foreground">
                  PNG, JPG, or WebP up to 2MB. Square format recommended.
                </p>
                <input
                  id="logo-upload"
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={handleLogoChange}
                  className="hidden"
                  disabled={isSubmitting}
                />
                {getFieldError("logo") && (
                  <p className="text-xs text-destructive">{getFieldError("logo")}</p>
                )}
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end space-x-3 pt-6 border-t">
            {mode === "create" ? (
              <>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => handleSubmit("draft")}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Save as Draft
                </Button>
                <Button
                  type="button"
                  onClick={() => handleSubmit("submit")}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Submit for Verification
                </Button>
              </>
            ) : (
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Save Clinic Changes
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
