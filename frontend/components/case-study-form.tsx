"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { caseStudies, type CaseStudy, type CaseStudyCreate } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";

interface Props {
  existing?: CaseStudy;
}

interface Iteration {
  input: string;
  output: string;
  notes: string;
}

export function CaseStudyForm({ existing }: Props) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const existingContent = existing?.content;
  const [title, setTitle] = useState(existing?.title ?? "");
  const [summary, setSummary] = useState(existing?.summary ?? "");
  const [aiModel, setAiModel] = useState(existing?.ai_model ?? "");
  const [aiPlatform, setAiPlatform] = useState(existing?.ai_platform ?? "");
  const [visibility, setVisibility] = useState<"public" | "private">(
    (existing?.visibility as "public" | "private") ?? "private",
  );
  const [tagsInput, setTagsInput] = useState(
    existing?.tags?.map((t) => t.name).join(", ") ?? "",
  );
  const [prompt, setPrompt] = useState(existingContent?.prompt ?? "");
  const [finalOutput, setFinalOutput] = useState(
    existingContent?.final_output ?? "",
  );
  const [iterations, setIterations] = useState<Iteration[]>(
    existingContent?.iterations?.map((i) => ({
      input: i.input,
      output: i.output,
      notes: i.notes ?? "",
    })) ?? [{ input: "", output: "", notes: "" }],
  );

  function addIteration() {
    if (iterations.length >= 50) return;
    setIterations([...iterations, { input: "", output: "", notes: "" }]);
  }

  function removeIteration(idx: number) {
    setIterations(iterations.filter((_, i) => i !== idx));
  }

  function updateIteration(idx: number, field: keyof Iteration, val: string) {
    setIterations(
      iterations.map((it, i) => (i === idx ? { ...it, [field]: val } : it)),
    );
  }

  async function handleSubmit(
    e: React.FormEvent,
    publishAfter = false,
  ) {
    e.preventDefault();
    setLoading(true);

    const data: CaseStudyCreate = {
      title,
      summary: summary || undefined,
      ai_model: aiModel || undefined,
      ai_platform: aiPlatform || undefined,
      visibility: publishAfter ? "public" : visibility,
      content: {
        prompt,
        iterations: iterations.filter((i) => i.input || i.output),
        final_output: finalOutput,
      },
      tags: tagsInput
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean)
        .slice(0, 10),
    };

    try {
      let cs: CaseStudy;
      if (existing) {
        cs = await caseStudies.update(existing.id, data);
        if (publishAfter) cs = await caseStudies.publish(existing.id);
      } else {
        cs = await caseStudies.create(data);
        if (publishAfter) cs = await caseStudies.publish(cs.id);
      }
      toast.success(publishAfter ? "Published!" : "Saved");
      router.push(`/${cs.author.handle}/${cs.slug}`);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={(e) => handleSubmit(e)} className="space-y-6 max-w-3xl">
      <div className="space-y-2">
        <Label htmlFor="title">Title *</Label>
        <Input
          id="title"
          required
          maxLength={300}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="What did you build or figure out?"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="ai_model">AI Model</Label>
          <Input
            id="ai_model"
            value={aiModel}
            onChange={(e) => setAiModel(e.target.value)}
            placeholder="e.g. GPT-4o, Claude 3.5"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="ai_platform">Platform</Label>
          <Input
            id="ai_platform"
            value={aiPlatform}
            onChange={(e) => setAiPlatform(e.target.value)}
            placeholder="e.g. ChatGPT, API, Cursor"
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="summary">Summary</Label>
        <Textarea
          id="summary"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          placeholder="Brief description of what this case study covers"
          rows={2}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="prompt">
          Prompt *{" "}
          <span className="text-xs text-muted-foreground">
            ({prompt.length}/10,000)
          </span>
        </Label>
        <Textarea
          id="prompt"
          required
          maxLength={10_000}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="The prompt(s) you used..."
          rows={5}
        />
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Label>Iterations ({iterations.length}/50)</Label>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={addIteration}
            disabled={iterations.length >= 50}
          >
            <Plus className="h-3.5 w-3.5 mr-1" />
            Add iteration
          </Button>
        </div>

        {iterations.map((iter, idx) => (
          <div
            key={idx}
            className="border rounded-lg p-4 space-y-3 bg-muted/30"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Iteration {idx + 1}
              </span>
              {iterations.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeIteration(idx)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Input / Prompt refinement</Label>
              <Textarea
                maxLength={20_000}
                value={iter.input}
                onChange={(e) => updateIteration(idx, "input", e.target.value)}
                rows={3}
                placeholder="What you sent to the AI..."
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Output / Response</Label>
              <Textarea
                maxLength={20_000}
                value={iter.output}
                onChange={(e) =>
                  updateIteration(idx, "output", e.target.value)
                }
                rows={3}
                placeholder="What the AI returned..."
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Notes</Label>
              <Input
                value={iter.notes}
                onChange={(e) => updateIteration(idx, "notes", e.target.value)}
                placeholder="What you observed or changed..."
              />
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <Label htmlFor="final_output">
          Final Output *{" "}
          <span className="text-xs text-muted-foreground">
            ({finalOutput.length}/50,000)
          </span>
        </Label>
        <Textarea
          id="final_output"
          required
          maxLength={50_000}
          value={finalOutput}
          onChange={(e) => setFinalOutput(e.target.value)}
          placeholder="The final result you achieved..."
          rows={5}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="tags">Tags (comma-separated, max 10)</Label>
        <Input
          id="tags"
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
          placeholder="writing, code, image-gen, productivity"
        />
      </div>

      <div className="flex gap-3 pt-2">
        <Button
          type="button"
          variant="outline"
          disabled={loading}
          onClick={(e) => handleSubmit(e as unknown as React.FormEvent)}
        >
          Save draft
        </Button>
        <Button
          type="button"
          disabled={loading}
          onClick={(e) =>
            handleSubmit(e as unknown as React.FormEvent, true)
          }
        >
          {loading ? "Publishing..." : "Publish"}
        </Button>
      </div>
    </form>
  );
}
