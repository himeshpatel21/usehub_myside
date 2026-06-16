"use client";

import { useEffect, useState } from "react";
import { feed as feedApi, type CaseStudyList, type SearchResults } from "@/lib/api";
import { CaseStudyCard } from "@/components/case-study-card";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";

export default function DiscoverPage() {
  const [trending, setTrending] = useState<CaseStudyList[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    feedApi.discover().then(setTrending).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!query.trim()) {
        setResults(null);
        return;
      }
      setSearching(true);
      try {
        const res = await feedApi.search(query.trim());
        setResults(res);
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const displayItems = results?.case_studies ?? trending;

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">Discover</h1>
        <p className="text-muted-foreground text-sm">
          Trending AI case studies from the community
        </p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          className="pl-9"
          placeholder="Search case studies and creators..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {results?.users && results.users.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-medium text-muted-foreground">People</h2>
          <div className="flex flex-wrap gap-2">
            {results.users.map((u) => (
              <a
                key={u.id}
                href={`/${u.handle}`}
                className="flex items-center gap-2 rounded-full border bg-card px-3 py-1 hover:bg-accent transition-colors"
              >
                <span className="text-sm font-medium">{u.name}</span>
                <span className="text-xs text-muted-foreground">@{u.handle}</span>
              </a>
            ))}
          </div>
        </div>
      )}

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 rounded-xl border bg-muted animate-pulse" />
          ))}
        </div>
      ) : displayItems.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          {query ? "No case studies found" : "No trending case studies yet"}
        </div>
      ) : (
        <div className="space-y-4">
          {!query && (
            <h2 className="text-sm font-medium text-muted-foreground">
              Trending this week
            </h2>
          )}
          {displayItems.map((cs) => (
            <CaseStudyCard key={cs.id} cs={cs} />
          ))}
        </div>
      )}
    </div>
  );
}
