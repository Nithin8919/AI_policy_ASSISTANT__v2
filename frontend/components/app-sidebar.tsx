"use client"

import * as React from "react"
import {
  ArrowUpCircleIcon,
  MessageSquare,
  Plus,
  SettingsIcon,
  Trash2,
  BookOpenIcon,
} from "lucide-react"

import { NavSecondary } from "@/components/nav-secondary"
import { NavUser } from "@/components/nav-user"
import { Button } from "@/components/ui/button"
import { SettingsDialog } from "@/components/SettingsDialog"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

const navSecondaryData = [
  {
    title: "Documentation",
    url: "/documentation",
    icon: BookOpenIcon,
  },
  {
    title: "Settings",
    url: "#",
    icon: SettingsIcon,
  },
]

interface ChatHistoryItem {
  id: string
  title: string
  preview: string
  timestamp: Date
}

interface AppSidebarProps extends React.ComponentProps<typeof Sidebar> {
  chatHistory?: ChatHistoryItem[]
  activeChatId?: string
  onNewChat?: () => void
  onSelectChat?: (chatId: string) => void
  onDeleteChat?: (chatId: string) => void
}

export function AppSidebar({
  chatHistory = [],
  activeChatId,
  onNewChat,
  onSelectChat,
  onDeleteChat,
  ...props
}: AppSidebarProps) {
  const formatTime = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (days === 0) {
      return 'Today'
    } else if (days === 1) {
      return 'Yesterday'
    } else if (days < 7) {
      return `${days} days ago`
    } else {
      return date.toLocaleDateString()
    }
  }

  // Default user data
  const userData = {
    name: 'User',
    email: 'user@gmail.com',
    avatar: '/avatars/default.jpg',
  }

  return (
    <Sidebar collapsible="offcanvas" {...props} className="flex flex-col">
      <SidebarHeader className="flex-shrink-0">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              className="data-[slot=sidebar-menu-button]:!p-1.5"
            >
              <a href="/">
                <ArrowUpCircleIcon className="h-5 w-5" />
                <span className="text-base font-semibold">Policy Assistant</span>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      {/* Scrollable Chat History Section */}
      <SidebarContent className="flex-1 overflow-y-auto min-h-0">
        <SidebarGroup className="flex flex-col">
          <SidebarGroupLabel className="flex items-center justify-between flex-shrink-0">
            <span>Recent Chats</span>
            {onNewChat && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={onNewChat}
              >
                <Plus className="h-4 w-4" />
              </Button>
            )}
          </SidebarGroupLabel>
          <SidebarGroupContent className="flex-1 overflow-y-auto sidebar-scrollbar min-h-0">
            <SidebarMenu>
              {chatHistory.length === 0 ? (
                <div className="px-2 py-4 text-center text-sm text-muted-foreground">
                  <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No conversations yet</p>
                  <p className="text-xs">Start a new chat to begin</p>
                </div>
              ) : (
                chatHistory.map((chat) => (
                  <SidebarMenuItem key={chat.id}>
                    <SidebarMenuButton
                      onClick={() => onSelectChat?.(chat.id)}
                      isActive={activeChatId === chat.id}
                      className="group relative w-full justify-start gap-3 h-auto py-3 px-3"
                    >
                      <MessageSquare className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate">
                          {chat.title}
                        </div>
                        <div className="text-xs text-muted-foreground truncate mt-0.5">
                          {chat.preview}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {formatTime(chat.timestamp)}
                        </div>
                      </div>
                      {onDeleteChat && (
                        <SidebarMenuAction
                          onClick={(e) => {
                            e.stopPropagation()
                            onDeleteChat(chat.id)
                          }}
                          className="opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <Trash2 className="h-4 w-4" />
                        </SidebarMenuAction>
                      )}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      {/* Fixed Bottom Section */}
      <SidebarFooter className="flex-shrink-0 flex flex-col gap-0 border-t border-border mt-auto">
        <NavSecondary
          items={navSecondaryData}
          customRenderers={{
            "Settings": (item) => (
              <SettingsDialog>
                <SidebarMenuButton asChild>
                  <button>
                    <item.icon />
                    <span>{item.title}</span>
                  </button>
                </SidebarMenuButton>
              </SettingsDialog>
            )
          }}
        />
        <NavUser
          user={userData}
        />
      </SidebarFooter>
    </Sidebar>
  )
}
