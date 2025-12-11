#!/usr/bin/env python3
"""
Diagnostic script to verify Google Cloud OAuth/ADC setup for Vertex AI.
Run this to check if your credentials are properly configured.
"""

import os
import sys

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed, skipping .env loading")

def check_oauth_setup():
    print("🔍 Checking Google Cloud OAuth/ADC Setup...\n")
    
    # 1. Check environment variables
    print("1️⃣ Environment Variables:")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-south1")
    service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    if project_id:
        print(f"   ✅ GOOGLE_CLOUD_PROJECT_ID: {project_id}")
    else:
        print("   ⚠️  GOOGLE_CLOUD_PROJECT_ID not set")
    
    print(f"   📍 GOOGLE_CLOUD_LOCATION: {location}")
    
    if service_account_file:
        if os.path.exists(service_account_file):
            print(f"   ✅ GOOGLE_APPLICATION_CREDENTIALS: {service_account_file}")
        else:
            print(f"   ❌ GOOGLE_APPLICATION_CREDENTIALS set but file not found: {service_account_file}")
    else:
        print("   ⚠️  GOOGLE_APPLICATION_CREDENTIALS not set (will use ADC)")
    
    print()
    
    # 2. Check google-auth
    print("2️⃣ Google Auth Library:")
    try:
        import google.auth
        print("   ✅ google-auth installed")
        
        # Try to get credentials
        try:
            if service_account_file and os.path.exists(service_account_file):
                from google.oauth2 import service_account
                scopes = ['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/generative-language.retriever']
                creds = service_account.Credentials.from_service_account_file(service_account_file, scopes=scopes)
                print(f"   ✅ Service account credentials loaded")
                if not project_id:
                    import json
                    with open(service_account_file, 'r') as f:
                        detected_project = json.load(f).get('project_id')
                else:
                    detected_project = project_id
            else:
                creds, detected_project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/generative-language.retriever'])
                print(f"   ✅ Default credentials found")
            print(f"   ✅ Default credentials found")
            print(f"   📦 Detected project: {detected_project or 'None'}")
            
            # Check scopes
            if hasattr(creds, 'scopes'):
                print(f"   🔐 Scopes: {creds.scopes}")
            else:
                print("   ⚠️  No scopes attribute (might need to add scopes)")
                
        except Exception as e:
            print(f"   ❌ Failed to get default credentials: {e}")
            print("\n   💡 Run: gcloud auth application-default login")
            return False
            
    except ImportError:
        print("   ❌ google-auth not installed")
        print("   💡 Run: pip install google-auth")
        return False
    
    # 3. Check google-genai
    print("\n3️⃣ Google GenAI SDK:")
    try:
        from google import genai
        print("   ✅ google-genai installed")
        
        # Try to create client
        try:
            final_project = project_id or detected_project
            if not final_project:
                print("   ❌ No project ID available")
                return False
                
            client = genai.Client(
                vertexai=True,
                project=final_project,
                location=location,
                credentials=creds,
            )
            print(f"   ✅ Vertex AI client created successfully")
            print(f"   🎯 Using project: {final_project}")
            print(f"   📍 Using location: {location}")
            
            # Try a simple API call
            try:
                print("\n4️⃣ Testing Vertex AI API Access:")
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[{"role": "user", "parts": [{"text": "Hello"}]}],
                    config={"max_output_tokens": 10}
                )
                print("   ✅ Vertex AI API call successful!")
                print(f"   📝 Response: {response.text[:50]}...")
                return True
                
            except Exception as e:
                error_str = str(e)
                print(f"   ❌ Vertex AI API call failed: {e}")
                
                if "invalid_scope" in error_str.lower():
                    print("\n   💡 SOLUTION: Your OAuth credentials need additional scopes.")
                    print("   Run these commands:")
                    print("   1. gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/generative-language.retriever")
                    print("   OR")
                    print("   2. gcloud auth application-default login --no-browser")
                    
                elif "403" in error_str or "PERMISSION_DENIED" in error_str:
                    print("\n   💡 SOLUTION: Your account needs Vertex AI permissions.")
                    print("   Run:")
                    print(f"   gcloud projects add-iam-policy-binding {final_project} \\")
                    print(f"       --member='user:YOUR_EMAIL@gmail.com' \\")
                    print(f"       --role='roles/aiplatform.user'")
                    
                return False
                
        except Exception as e:
            print(f"   ❌ Failed to create Vertex AI client: {e}")
            return False
            
    except ImportError:
        print("   ❌ google-genai not installed")
        print("   💡 Run: pip install google-genai")
        return False

if __name__ == "__main__":
    success = check_oauth_setup()
    
    if success:
        print("\n✅ All checks passed! Your OAuth/Vertex AI setup is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ OAuth/Vertex AI setup has issues. Please follow the solutions above.")
        sys.exit(1)
