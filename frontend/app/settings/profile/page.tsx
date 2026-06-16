"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { users as usersApi, type UserPublic } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { AvatarUpload } from "@/components/avatar-upload";
import { toast } from "sonner";

export default function ProfileSettingsPage() {
  const { user, loading, refresh } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<UserPublic | null>(null);
  const [saving, setSaving] = useState(false);

  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [aiSince, setAiSince] = useState("");
  const [location, setLocation] = useState("");
  const [website, setWebsite] = useState("");
  const [twitter, setTwitter] = useState("");
  const [githubUsername, setGithubUsername] = useState("");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  useEffect(() => {
    if (user) {
      usersApi.getByHandle(user.handle).then((p) => {
        setProfile(p);
        setName(p.name);
        setAvatarUrl(p.avatar_url);
        if (p.profile) {
          setBio(p.profile.bio ?? "");
          setAiSince(p.profile.ai_since ?? "");
          setLocation(p.profile.location ?? "");
          setWebsite(p.profile.website ?? "");
          setTwitter(p.profile.twitter ?? "");
          setGithubUsername(p.profile.github_username ?? "");
        }
      });
    }
  }, [user]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await usersApi.updateMe({
        name,
        bio,
        ai_since: aiSince || undefined,
        location,
        website,
        twitter,
        github_username: githubUsername,
        avatar_url: avatarUrl ?? undefined,
      } as Parameters<typeof usersApi.updateMe>[0]);
      await refresh();
      toast.success("Profile updated");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading || !user) return null;

  return (
    <div className="max-w-xl space-y-6">
      <h1 className="text-2xl font-bold">Profile settings</h1>

      <form onSubmit={handleSave} className="space-y-5">
        <AvatarUpload
          currentUrl={avatarUrl}
          name={name || user.name}
          onUploaded={setAvatarUrl}
        />

        <div className="space-y-2">
          <Label htmlFor="name">Display name</Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={100}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="bio">Bio</Label>
          <Textarea
            id="bio"
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            maxLength={1000}
            rows={3}
            placeholder="Tell the community about yourself..."
          />
          <p className="text-xs text-muted-foreground">{bio.length}/1000</p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="ai_since">Using AI since</Label>
            <Input
              id="ai_since"
              type="date"
              value={aiSince}
              onChange={(e) => setAiSince(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="location">Location</Label>
            <Input
              id="location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              maxLength={100}
              placeholder="City, Country"
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="website">Website</Label>
          <Input
            id="website"
            type="url"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            maxLength={255}
            placeholder="https://yourwebsite.com"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="twitter">Twitter / X handle</Label>
            <Input
              id="twitter"
              value={twitter}
              onChange={(e) => setTwitter(e.target.value)}
              maxLength={100}
              placeholder="@handle"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="github">GitHub username</Label>
            <Input
              id="github"
              value={githubUsername}
              onChange={(e) => setGithubUsername(e.target.value)}
              maxLength={100}
            />
          </div>
        </div>

        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save changes"}
        </Button>
      </form>
    </div>
  );
}
