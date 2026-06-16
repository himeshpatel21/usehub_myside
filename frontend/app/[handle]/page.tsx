import { notFound } from "next/navigation";
import Link from "next/link";
import { caseStudies as csApi, users as usersApi } from "@/lib/api";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { CaseStudyCard } from "@/components/case-study-card";
import { CalendarDays, Globe, MapPin } from "lucide-react";

interface Props {
  params: Promise<{ handle: string }>;
}

export default async function ProfilePage({ params }: Props) {
  const { handle } = await params;

  let user;
  try {
    user = await usersApi.getByHandle(handle);
  } catch {
    notFound();
  }

  const caseStudyList = await csApi
    .byUser(handle)
    .catch(() => []);

  const profile = user.profile;

  return (
    <div className="space-y-8">
      <div className="flex gap-6">
        <Avatar className="h-20 w-20 shrink-0">
          <AvatarImage src={user.avatar_url ?? undefined} />
          <AvatarFallback className="text-2xl">
            {user.name[0]?.toUpperCase()}
          </AvatarFallback>
        </Avatar>

        <div className="flex-1 space-y-2">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-bold">{user.name}</h1>
              <p className="text-muted-foreground text-sm">@{user.handle}</p>
            </div>
          </div>

          {profile?.bio && (
            <p className="text-sm leading-relaxed">{profile.bio}</p>
          )}

          <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
            {profile?.location && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5" />
                {profile.location}
              </span>
            )}
            {profile?.website && (
              <a
                href={profile.website}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 hover:text-foreground transition-colors"
              >
                <Globe className="h-3.5 w-3.5" />
                {profile.website.replace(/^https?:\/\//, "")}
              </a>
            )}
            {profile?.twitter && (
              <a
                href={`https://twitter.com/${profile.twitter.replace("@", "")}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 hover:text-foreground transition-colors"
              >
                𝕏 {profile.twitter}
              </a>
            )}
            {profile?.ai_since && (
              <span className="flex items-center gap-1">
                <CalendarDays className="h-3.5 w-3.5" />
                Using AI since {new Date(profile.ai_since).getFullYear()}
              </span>
            )}
          </div>

          <div className="flex gap-4 text-sm">
            <span>
              <strong>{user.followers_count}</strong>{" "}
              <span className="text-muted-foreground">followers</span>
            </span>
            <span>
              <strong>{user.following_count}</strong>{" "}
              <span className="text-muted-foreground">following</span>
            </span>
            <span>
              <strong>{caseStudyList.length}</strong>{" "}
              <span className="text-muted-foreground">case studies</span>
            </span>
          </div>

          {profile?.tools && profile.tools.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {profile.tools.map((ut, i) => (
                <Badge key={i} variant="outline" className="text-xs">
                  {ut.tool?.name ?? ut.custom_tool_name}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </div>

      <Separator />

      <div className="space-y-4">
        <h2 className="font-semibold">Case Studies</h2>
        {caseStudyList.length === 0 ? (
          <p className="text-muted-foreground text-sm">No public case studies yet.</p>
        ) : (
          caseStudyList.map((cs) => <CaseStudyCard key={cs.id} cs={cs} />)
        )}
      </div>
    </div>
  );
}
