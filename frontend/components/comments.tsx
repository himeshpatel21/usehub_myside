"use client";

import { useEffect, useState } from "react";
import { engagement, type Comment } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import { formatDistanceToNow } from "@/lib/utils";

interface Props {
  caseStudyId: string;
}

export function Comments({ caseStudyId }: Props) {
  const { user } = useAuth();
  const [comments, setComments] = useState<Comment[]>([]);
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    engagement.comments(caseStudyId).then(setComments).catch(() => {});
  }, [caseStudyId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    setSubmitting(true);
    try {
      const comment = await engagement.addComment(caseStudyId, body.trim());
      setComments((prev) => [...prev, comment]);
      setBody("");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to post comment");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(commentId: string) {
    try {
      await engagement.deleteComment(commentId);
      setComments((prev) =>
        prev.map((c) =>
          c.id === commentId ? { ...c, body: "[deleted]", deleted_at: new Date().toISOString() } : c,
        ),
      );
    } catch {
      toast.error("Failed to delete comment");
    }
  }

  return (
    <div className="space-y-6">
      <h3 className="font-semibold text-sm">
        {comments.length} comment{comments.length !== 1 ? "s" : ""}
      </h3>

      {user && (
        <form onSubmit={handleSubmit} className="flex gap-3">
          <Avatar className="h-7 w-7 shrink-0">
            <AvatarImage src={user.avatar_url ?? undefined} />
            <AvatarFallback className="text-xs">
              {user.name[0]?.toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 space-y-2">
            <Textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              maxLength={2000}
              placeholder="Add a comment..."
              rows={2}
              className="resize-none"
            />
            <div className="flex justify-between items-center">
              <span className="text-xs text-muted-foreground">
                {body.length}/2000
              </span>
              <Button
                type="submit"
                size="sm"
                disabled={submitting || !body.trim()}
              >
                {submitting ? "Posting..." : "Comment"}
              </Button>
            </div>
          </div>
        </form>
      )}

      <div className="space-y-4">
        {comments.map((comment) => (
          <div key={comment.id} className="flex gap-3">
            <Avatar className="h-7 w-7 shrink-0">
              <AvatarImage src={comment.author.avatar_url ?? undefined} />
              <AvatarFallback className="text-xs">
                {comment.author.name[0]?.toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">
                    {comment.author.name}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatDistanceToNow(comment.created_at)}
                  </span>
                </div>
                {user?.id === comment.author.id && !comment.deleted_at && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    onClick={() => handleDelete(comment.id)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                )}
              </div>
              <p
                className={`text-sm mt-0.5 ${
                  comment.deleted_at ? "text-muted-foreground italic" : ""
                }`}
              >
                {comment.body}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
