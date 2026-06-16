"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { CaseStudyForm } from "@/components/case-study-form";

export default function NewCaseStudyPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  if (loading || !user) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">New case study</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Document your prompt, iterations, and final outcome.
        </p>
      </div>
      <CaseStudyForm />
    </div>
  );
}
