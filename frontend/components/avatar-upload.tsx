"use client";

import { useRef, useState } from "react";
import { users } from "@/lib/api";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { toast } from "sonner";
import { Upload } from "lucide-react";

interface Props {
  currentUrl: string | null;
  name: string;
  onUploaded: (url: string) => void;
}

export function AvatarUpload({ currentUrl, name, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  async function handleFile(file: File) {
    if (!file.type.startsWith("image/")) {
      toast.error("Please select an image file");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error("Image must be under 5MB");
      return;
    }

    setPreview(URL.createObjectURL(file));
    setUploading(true);

    try {
      const { upload_url, public_url } = await users.avatarUploadUrl(file.type);
      await fetch(upload_url, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type },
      });
      onUploaded(public_url);
      toast.success("Avatar updated");
    } catch {
      toast.error("Upload failed");
      setPreview(null);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="flex items-center gap-4">
      <div
        className="relative cursor-pointer group"
        onClick={() => inputRef.current?.click()}
      >
        <Avatar className="h-16 w-16">
          <AvatarImage src={preview ?? currentUrl ?? undefined} />
          <AvatarFallback className="text-xl">
            {name[0]?.toUpperCase()}
          </AvatarFallback>
        </Avatar>
        <div className="absolute inset-0 flex items-center justify-center rounded-full bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity">
          <Upload className="h-5 w-5 text-white" />
        </div>
        {uploading && (
          <div className="absolute inset-0 flex items-center justify-center rounded-full bg-black/60">
            <div className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
          </div>
        )}
      </div>
      <div className="text-sm text-muted-foreground">
        <p>Click to upload new photo</p>
        <p className="text-xs">JPG, PNG, WebP, GIF — max 5MB</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />
    </div>
  );
}
