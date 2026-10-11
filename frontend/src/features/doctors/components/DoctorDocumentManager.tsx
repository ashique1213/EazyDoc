import React, { useState } from "react";
import axios from "axios";
import { AlertCircle, FileCheck, FileText, Loader2, Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import type { DoctorDocument } from "../types";
import { useDoctorDocuments, useUploadDoctorDocument, useDeleteDoctorDocument } from "../hooks";

export const DoctorDocumentManager: React.FC = () => {
  const { data: documents = [], isLoading } = useDoctorDocuments();
  const uploadMutation = useUploadDoctorDocument();
  const deleteMutation = useDeleteDoctorDocument();

  const [documentType, setDocumentType] = useState<string>("REGISTRATION_CERTIFICATE");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setErrorMsg(null);
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        setErrorMsg("File size must not exceed 5MB.");
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMsg("Please select a file to upload.");
      return;
    }

    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await uploadMutation.mutateAsync({
        documentType,
        file: selectedFile,
      });
      setSelectedFile(null);
      setSuccessMsg("Document uploaded securely.");
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        const data = err.response?.data as { message?: string } | undefined;
        setErrorMsg(data?.message || "Failed to upload document.");
      } else {
        setErrorMsg("Failed to upload document.");
      }
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Are you sure you want to remove this document?")) return;
    try {
      await deleteMutation.mutateAsync(id);
    } catch {
      alert("Failed to delete document.");
    }
  };

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle className="text-xl">Registration Evidence & Certificates</CardTitle>
        <CardDescription>
          Upload your medical registration certificate, degrees, or ID proof for Super Admin review.
          Files are stored privately and never displayed publicly.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {errorMsg && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{errorMsg}</AlertDescription>
          </Alert>
        )}

        {successMsg && (
          <Alert className="border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:text-emerald-300">
            <FileCheck className="h-4 w-4 text-emerald-600" />
            <AlertTitle>Success</AlertTitle>
            <AlertDescription>{successMsg}</AlertDescription>
          </Alert>
        )}

        {/* Upload form */}
        <form onSubmit={handleUpload} className="rounded-xl border bg-muted/20 p-4 space-y-4">
          <h4 className="text-sm font-semibold">Upload New Verification Evidence</h4>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="document_type">Document Category</Label>
              <select
                id="document_type"
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                <option value="REGISTRATION_CERTIFICATE">
                  Medical Registration Certificate
                </option>
                <option value="DEGREE_CERTIFICATE">
                  Degree / Qualification Certificate
                </option>
                <option value="GOVERNMENT_ID">Government Identity Proof</option>
                <option value="OTHER">Other Supporting Document</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="doc_file">Select Document (PDF, JPG, PNG)</Label>
              <Input
                id="doc_file"
                type="file"
                accept=".pdf,image/jpeg,image/png,image/webp"
                onChange={handleFileChange}
                className="text-xs file:mr-2 file:py-1 file:px-2 file:rounded-md file:border-0 file:text-xs file:bg-primary file:text-primary-foreground"
              />
              <span className="text-[10px] text-muted-foreground">Max 5MB per document</span>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <Button
              type="submit"
              disabled={!selectedFile || uploadMutation.isPending}
              size="sm"
              className="gap-2"
            >
              {uploadMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              Upload Document
            </Button>
          </div>
        </form>

        {/* Uploaded Documents List */}
        <div className="space-y-3">
          <h4 className="text-sm font-semibold">Uploaded Evidence ({documents.length})</h4>
          {isLoading ? (
            <div className="flex items-center justify-center p-6 text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading documents...
            </div>
          ) : documents.length === 0 ? (
            <div className="rounded-lg border border-dashed p-6 text-center text-xs text-muted-foreground">
              No verification documents uploaded yet. Adding your registration certificate expedites admin approval.
            </div>
          ) : (
            <div className="divide-y rounded-lg border">
              {documents.map((doc: DoctorDocument) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between p-3 text-xs hover:bg-muted/30 transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <FileText className="h-5 w-5 text-primary shrink-0" />
                    <div className="min-w-0 truncate">
                      <p className="font-semibold text-foreground truncate">{doc.file_name}</p>
                      <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                        <Badge variant="outline" className="text-[10px] py-0">
                          {doc.document_type_display}
                        </Badge>
                        <span>{(doc.file_size / (1024 * 1024)).toFixed(2)} MB</span>
                        <span>•</span>
                        <span>{new Date(doc.uploaded_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>

                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDelete(doc.id)}
                    disabled={deleteMutation.isPending}
                    className="h-8 w-8 text-destructive hover:bg-destructive/10"
                    title="Delete document"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
