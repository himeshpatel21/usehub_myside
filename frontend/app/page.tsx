import Link from "next/link";
import { Button } from "@/components/ui/button";
import { BookOpen, Sparkles, Users } from "lucide-react";

export default function HomePage() {
  return (
    <div className="flex flex-col items-center text-center gap-10 py-16">
      <div className="flex flex-col items-center gap-4 max-w-2xl">
        <div className="flex items-center gap-2 text-sm text-muted-foreground bg-muted px-3 py-1 rounded-full">
          <Sparkles className="h-3.5 w-3.5" />
          The GitHub for AI case studies
        </div>
        <h1 className="text-5xl font-bold tracking-tight">
          Share how you work with AI
        </h1>
        <p className="text-xl text-muted-foreground leading-relaxed">
          Document your prompts, show your iterations, and inspire others.
          UseHub is the place to share real AI case studies — not just the final
          result.
        </p>
        <div className="flex gap-3 mt-2">
          <Button asChild size="lg">
            <Link href="/login">Get started free</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/discover">Browse case studies</Link>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-3xl mt-4">
        {[
          {
            icon: BookOpen,
            title: "Structured case studies",
            desc: "Show your prompt, iterations, and final output. Not just the result.",
          },
          {
            icon: Users,
            title: "Social layer",
            desc: "Follow creators, react to posts, and discover what the community is building.",
          },
          {
            icon: Sparkles,
            title: "Built for iteration",
            desc: "Every edit is versioned. Your AI journey is preserved, not overwritten.",
          },
        ].map(({ icon: Icon, title, desc }) => (
          <div
            key={title}
            className="flex flex-col gap-2 rounded-xl border bg-card p-6 text-left"
          >
            <Icon className="h-6 w-6 text-primary" />
            <h3 className="font-semibold">{title}</h3>
            <p className="text-sm text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
