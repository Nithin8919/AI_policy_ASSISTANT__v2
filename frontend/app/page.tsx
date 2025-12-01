'use client'

import Link from 'next/link'
import Image from 'next/image'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MessageSquare, Brain, Shield, Zap, BookOpen, ArrowRight } from 'lucide-react'
import { ThemeToggle } from '@/components/ThemeToggle'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Logo in top left corner */}
      <div className="absolute top-3 left-3 sm:top-6 sm:left-6 z-50">
        <div className="bg-primary/10 rounded-lg p-1.5 sm:p-2 md:p-3 border border-border will-change-transform">
          <Image
            src="/Techbharat_logo.png"
            alt="TechBharat Logo"
            width={60}
            height={20}
            className="object-contain w-[60px] h-[20px] sm:w-[80px] sm:h-[27px] md:w-[100px] md:h-[33px]"
            priority
            loading="eager"
          />
        </div>
      </div>

      {/* Theme toggle in top right corner */}
      <div className="absolute top-3 right-3 sm:top-6 sm:right-6 z-50">
        <ThemeToggle />
      </div>

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        <div className="max-w-6xl mx-auto">
          {/* Hero Section */}
          <div className="text-center mb-12 sm:mb-16">
            <div className="inline-flex items-center gap-2 bg-primary/10 text-primary px-3 sm:px-4 py-1.5 sm:py-2 rounded-full text-xs sm:text-sm font-medium mb-4 sm:mb-6">
              <Brain className="h-3 w-3 sm:h-4 sm:w-4" />
              <span className="hidden sm:inline">AI-Powered Education Policy Assistant</span>
              <span className="sm:hidden">AI Policy Assistant</span>
            </div>
            <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-foreground mb-4 sm:mb-6 px-4 will-change-transform">
              GITAM Policy AI
            </h1>
            <p className="text-base sm:text-lg md:text-xl text-muted-foreground mb-6 sm:mb-8 max-w-3xl mx-auto leading-relaxed px-4 will-change-transform">
              Get instant, accurate answers about GITAM education policies with comprehensive citations and real-time processing insights.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center px-4">
                <Link href="/chat" className="w-full sm:w-auto">
                  <Button size="lg" className="w-full sm:w-auto px-6 sm:px-8 py-3 text-base sm:text-lg bg-orange-600 hover:bg-orange-700 text-white">
                    <MessageSquare className="h-4 w-4 sm:h-5 sm:w-5 mr-2" />
                    Start Chatting
                  </Button>
                </Link>
              <Link href="/documentation" className="w-full sm:w-auto">
                <Button size="lg" className="w-full sm:w-auto px-6 sm:px-8 py-3 text-base sm:text-lg bg-orange-600 hover:bg-orange-700 text-white">
                  <BookOpen className="h-4 w-4 sm:h-5 sm:w-5 mr-2" />
                  View Documentation
                </Button>
              </Link>
            </div>
          </div>

          {/* Features Grid */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 lg:gap-8 mb-12 sm:mb-16 px-4">
            <Card className="bg-card border-border hover:bg-accent/50 transition-colors">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 sm:gap-3 text-base sm:text-lg">
                  <div className="w-8 h-8 sm:w-10 sm:h-10 bg-orange-500/10 rounded-lg flex items-center justify-center shrink-0">
                    <Brain className="h-4 w-4 sm:h-5 sm:w-5 text-orange-500" />
                  </div>
                  Intelligent Processing
                </CardTitle>
                <CardDescription className="text-sm">
                  Advanced AI with multi-modal retrieval and language understanding
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-xs sm:text-sm text-muted-foreground">
                  Combines dense embeddings, sparse search, and knowledge graph traversal for comprehensive answers.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-card border-border hover:bg-accent/50 transition-colors">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 sm:gap-3 text-base sm:text-lg">
                  <div className="w-8 h-8 sm:w-10 sm:h-10 bg-green-500/10 rounded-lg flex items-center justify-center shrink-0">
                    <Shield className="h-4 w-4 sm:h-5 sm:w-5 text-green-500" />
                  </div>
                  Verified Citations
                </CardTitle>
                <CardDescription className="text-sm">
                  Every answer backed by verifiable sources and exact document locations
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-xs sm:text-sm text-muted-foreground">
                  Complete audit trail with document references, page numbers, and text spans for transparency.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-card border-border hover:bg-accent/50 transition-colors">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 sm:gap-3 text-base sm:text-lg">
                  <div className="w-8 h-8 sm:w-10 sm:h-10 bg-purple-500/10 rounded-lg flex items-center justify-center shrink-0">
                    <Zap className="h-4 w-4 sm:h-5 sm:w-5 text-purple-500" />
                  </div>
                  Real-time Insights
                </CardTitle>
                <CardDescription className="text-sm">
                  Live processing traces and system monitoring for developers
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-xs sm:text-sm text-muted-foreground">
                  Step-by-step visibility into query processing, retrieval, and LLM controller iterations.
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Status Banner */}
          <Card className="border-[#e68058]/20 bg-[#e68058]/5 mb-12 sm:mb-16 mx-4">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base sm:text-lg" style={{ color: '#e68058' }}>
                <Zap className="h-4 w-4 sm:h-5 sm:w-5" />
                Prototype Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm sm:text-base leading-relaxed" style={{ color: 'rgba(230, 128, 88, 0.8)' }}>
                This is a high-accuracy prototype demonstrating the complete architecture and UI flow.
                All endpoints return placeholder data ("N/A" or "Coming soon") until integration with
                vector databases, knowledge graphs, and LLM services is complete.
              </p>
            </CardContent>
          </Card>

          {/* Call to Action */}
            <div className="text-center bg-gradient-to-r from-orange-600/10 to-orange-600/5 rounded-2xl p-6 sm:p-8 md:p-12 border border-orange-600/20 mx-4">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-foreground mb-3 sm:mb-4">
              Ready to Experience the Future?
            </h2>
            <p className="text-base sm:text-lg text-muted-foreground mb-6 sm:mb-8 max-w-2xl mx-auto px-4">
              Try the modern ChatGPT-style interface and see how AI can transform education policy research.
            </p>
            <Link href="/chat">
                <Button size="lg" className="px-8 sm:px-12 py-3 sm:py-4 text-base sm:text-lg bg-orange-600 hover:bg-orange-700 text-white group">
                <MessageSquare className="h-4 w-4 sm:h-5 sm:w-5 mr-2" />
                Start Your First Chat
                <ArrowRight className="h-4 w-4 sm:h-5 sm:w-5 ml-2 group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
