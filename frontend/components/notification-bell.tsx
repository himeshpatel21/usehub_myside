"use client";

import { useEffect, useState } from "react";
import { notifications as notifApi, type Notification } from "@/lib/api";
import { Bell } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function NotificationBell() {
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    notifApi.unreadCount().then((d) => setUnread(d.count)).catch(() => {});
    const interval = setInterval(() => {
      notifApi.unreadCount().then((d) => setUnread(d.count)).catch(() => {});
    }, 30_000);
    return () => clearInterval(interval);
  }, []);

  async function handleOpen(isOpen: boolean) {
    setOpen(isOpen);
    if (isOpen) {
      const data = await notifApi.list(10).catch(() => []);
      setItems(data);
      if (unread > 0) {
        await notifApi.markRead().catch(() => {});
        setUnread(0);
      }
    }
  }

  function formatMessage(n: Notification): string {
    const actor = n.payload.actor_name ?? n.payload.actor_handle ?? "Someone";
    if (n.type === "reaction")
      return `${actor} reacted with ${n.payload.reaction_type} to "${n.payload.case_study_title}"`;
    if (n.type === "comment")
      return `${actor} commented on "${n.payload.case_study_title}"`;
    if (n.type === "follow") return `${actor} started following you`;
    return n.type;
  }

  return (
    <DropdownMenu open={open} onOpenChange={handleOpen}>
      <DropdownMenuTrigger asChild>
        <button className="relative p-1.5 rounded-md hover:bg-accent transition-colors outline-none">
          <Bell className="h-4 w-4" />
          {unread > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] text-white font-bold">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel>Notifications</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {items.length === 0 ? (
          <div className="px-3 py-6 text-center text-sm text-muted-foreground">
            No notifications yet
          </div>
        ) : (
          items.map((n) => (
            <DropdownMenuItem key={n.id} className="flex-col items-start gap-0.5 py-2">
              <span className="text-sm">{formatMessage(n)}</span>
              <span className="text-xs text-muted-foreground">
                {new Date(n.created_at).toLocaleDateString()}
              </span>
            </DropdownMenuItem>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
