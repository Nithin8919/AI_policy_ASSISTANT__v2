"use client"

import { useState } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, FileText, Download, Copy, Check } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { queryAPI } from "@/lib/api"

export default function PolicyCrafterPage() {
    const [topic, setTopic] = useState("")
    const [isGenerating, setIsGenerating] = useState(false)
    const [generatedPolicy, setGeneratedPolicy] = useState("")
    const [copied, setCopied] = useState(false)

    const handleGenerate = async () => {
        if (!topic.trim()) return

        setIsGenerating(true)
        setGeneratedPolicy("")

        try {
            const response = await queryAPI({
                query: topic,
                mode: "policy_draft",
                internet_enabled: true
            })

            setGeneratedPolicy(response.answer)
        } catch (error) {
            console.error("Error generating policy:", error)
            setGeneratedPolicy("⚠️ Failed to generate policy. Please ensure the backend server is running.")
        } finally {
            setIsGenerating(false)
        }
    }

    const handleCopy = () => {
        navigator.clipboard.writeText(generatedPolicy)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    const handleDownload = () => {
        const element = document.createElement("a")
        const file = new Blob([generatedPolicy], { type: "text/markdown" })
        element.href = URL.createObjectURL(file)
        element.download = "draft-policy.md"
        document.body.appendChild(element)
        element.click()
        document.body.removeChild(element)
    }

    return (
        <SidebarProvider>
            <AppSidebar />
            <SidebarInset>
                <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
                    <SidebarTrigger className="-ml-1" />
                    <Separator orientation="vertical" className="mr-2 h-4" />
                    <h1 className="text-lg font-semibold">Policy Crafter</h1>
                </header>
                <div className="flex flex-1 flex-col gap-4 p-4 md:p-8 max-w-5xl mx-auto w-full">
                    <div className="grid gap-6 md:grid-cols-[1fr_1.5fr] h-[calc(100vh-8rem)]">

                        {/* Input Section */}
                        <div className="flex flex-col gap-4 h-full">
                            <Card className="h-full flex flex-col">
                                <CardHeader>
                                    <CardTitle>Draft New Policy</CardTitle>
                                    <CardDescription>
                                        Describe the policy you want to create. Include objectives, scope, and key requirements.
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="flex-1 flex flex-col gap-4">
                                    <Textarea
                                        placeholder="E.g., Draft a comprehensive policy for integrating AI in government schools, focusing on infrastructure, teacher training, and ethical guidelines..."
                                        className="flex-1 resize-none p-4 text-base"
                                        value={topic}
                                        onChange={(e) => setTopic(e.target.value)}
                                    />
                                    <Button
                                        onClick={handleGenerate}
                                        disabled={!topic.trim() || isGenerating}
                                        className="w-full"
                                        size="lg"
                                    >
                                        {isGenerating ? (
                                            <>
                                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                Drafting Policy...
                                            </>
                                        ) : (
                                            <>
                                                <FileText className="mr-2 h-4 w-4" />
                                                Generate Draft
                                            </>
                                        )}
                                    </Button>
                                </CardContent>
                            </Card>
                        </div>

                        {/* Output Section */}
                        <div className="flex flex-col gap-4 h-full overflow-hidden">
                            <Card className="h-full flex flex-col overflow-hidden">
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 border-b">
                                    <div className="space-y-1">
                                        <CardTitle>Generated Draft</CardTitle>
                                        <CardDescription>
                                            Review and edit your policy draft
                                        </CardDescription>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            onClick={handleCopy}
                                            disabled={!generatedPolicy}
                                            title="Copy to clipboard"
                                        >
                                            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            onClick={handleDownload}
                                            disabled={!generatedPolicy}
                                            title="Download as Markdown"
                                        >
                                            <Download className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </CardHeader>
                                <CardContent className="flex-1 overflow-y-auto p-6 bg-muted/20">
                                    {generatedPolicy ? (
                                        <div className="prose prose-sm dark:prose-invert max-w-none">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {generatedPolicy}
                                            </ReactMarkdown>
                                        </div>
                                    ) : (
                                        <div className="h-full flex flex-col items-center justify-center text-muted-foreground p-8 text-center">
                                            <FileText className="h-12 w-12 mb-4 opacity-20" />
                                            <p>Your generated policy draft will appear here.</p>
                                            <p className="text-sm mt-2 opacity-60">Enter your requirements on the left to begin.</p>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </div>

                    </div>
                </div>
            </SidebarInset>
        </SidebarProvider>
    )
}
