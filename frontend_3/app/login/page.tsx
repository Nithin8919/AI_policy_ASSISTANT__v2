'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Brain, Loader2 } from 'lucide-react'
import { ThemeToggle } from '@/components/ThemeToggle'

export default function LoginPage() {
  const router = useRouter()
  const [signingIn, setSigningIn] = useState(false)

  const handleGoogleSignIn = async () => {
    setSigningIn(true)
    // Simulate sign in delay
    await new Promise(resolve => setTimeout(resolve, 1000))
    // Navigate to chat page
    router.push('/chat')
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center p-4 sm:p-6">
      {/* Logo in top left corner */}
      <div className="absolute top-3 left-3 sm:top-6 sm:left-6 z-50">
        <div className="bg-primary/10 backdrop-blur-sm rounded-lg p-1.5 sm:p-2 md:p-3 border border-border">
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

      <Card className="w-full max-w-sm sm:max-w-md bg-card border-border backdrop-blur-sm">
        <CardHeader className="space-y-3 sm:space-y-4">
          <div className="flex justify-center">
            <div className="w-12 h-12 sm:w-16 sm:h-16 bg-orange-500/10 rounded-2xl flex items-center justify-center">
              <Brain className="h-8 w-8 sm:h-10 sm:w-10 text-orange-500" />
            </div>
          </div>
          <CardTitle className="text-2xl sm:text-3xl font-bold text-center text-foreground">
            Welcome to Policy Assistant
          </CardTitle>
          <CardDescription className="text-center text-muted-foreground text-sm sm:text-base">
            Sign in to access AI-powered education policy assistance
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 sm:space-y-4">
          <Button
            onClick={handleGoogleSignIn}
            disabled={signingIn}
            className="w-full bg-orange-600 hover:bg-orange-700 text-white font-medium py-5 sm:py-6 text-sm sm:text-base"
            size="lg"
          >
            {signingIn ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Signing in...
              </>
            ) : (
              <>
                <svg className="mr-2 h-5 w-5" viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="currentColor"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                Continue with Google
              </>
            )}
          </Button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">
                Secure Authentication
              </span>
            </div>
          </div>

          <div className="text-center text-xs sm:text-sm text-muted-foreground px-2">
            By signing in, you agree to our Terms of Service and Privacy Policy
          </div>
        </CardContent>
      </Card>

      {/* Background decoration */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-48 w-96 h-96 bg-orange-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-1/4 -right-48 w-96 h-96 bg-orange-500/10 rounded-full blur-3xl"></div>
      </div>
    </div>
  )
}
