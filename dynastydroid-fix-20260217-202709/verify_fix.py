#!/usr/bin/env python3
"""
Verify the deployment fix works
"""
import sys
import os

def verify_files():
    print("Verifying fix files...")
    
    required_files = [
        ('render.yaml', 'services:'),
        ('main.py', 'register_bot'),
        ('requirements.txt', 'fastapi'),
        ('runtime.txt', 'python-3.11.0'),
        ('register.html', '<html'),
        ('dynastydroid-simple.html', '<html')
    ]
    
    all_good = True
    for filename, contains in required_files:
        if not os.path.exists(filename):
            print(f"❌ Missing: {filename}")
            all_good = False
            continue
            
        with open(filename, 'r') as f:
            content = f.read()
            if contains in content:
                print(f"✅ {filename} - OK")
            else:
                print(f"⚠️  {filename} - missing expected content '{contains}'")
    
    return all_good

def check_main_py():
    print("\nChecking main.py...")
    try:
        # Try to import main.py to verify it works
        import importlib.util
        spec = importlib.util.spec_from_file_location("main", "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'app'):
            app = module.app
            print(f"✅ App loaded: {app.title}")
            
            # Check for registration endpoint
            registration_found = False
            for route in app.routes:
                if hasattr(route, 'path') and '/api/v1/bots/register' in route.path:
                    registration_found = True
                    print(f"✅ Registration endpoint found: {route.path}")
                    break
            
            if not registration_found:
                print("❌ Registration endpoint not found in routes")
                return False
                
            return True
        else:
            print("❌ No app object in main.py")
            return False
            
    except Exception as e:
        print(f"❌ Error loading main.py: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("DynastyDroid Deployment Fix Verification")
    print("=" * 50)
    
    files_ok = verify_files()
    if not files_ok:
        print("\n❌ Missing or incorrect files")
        sys.exit(1)
    
    main_ok = check_main_py()
    
    print("\n" + "=" * 50)
    if files_ok and main_ok:
        print("✅ ALL CHECKS PASSED!")
        print("\nNext steps:")
        print("1. Push these files to GitHub:")
        print("   git add render.yaml")
        print("   git commit -m 'FIX: Correct Render configuration'")
        print("   git push origin main")
        print("\n2. Delete incorrect file:")
        print("   git rm render_updated.yaml")
        print("   git commit -m 'REMOVE: Incorrect render configuration'")
        print("   git push origin main")
        print("\n3. Render will auto-deploy within 5-10 minutes")
    else:
        print("❌ Fix verification failed")
        sys.exit(1)
