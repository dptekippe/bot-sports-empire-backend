// Safari JavaScript test script for DynastyDroid
// This will work once "Allow JavaScript from Apple Events" is enabled

function testDynastyDroid() {
    console.log("=== DynastyDroid Automated Test ===");
    
    // 1. Check page basics
    const pageTitle = document.title;
    console.log("Page Title:", pageTitle);
    
    // 2. Find all links
    const links = Array.from(document.querySelectorAll('a'));
    console.log("\nFound", links.length, "links on page");
    
    // 3. Look for registration link
    const registerLinks = links.filter(link => 
        link.textContent.includes('Register') || 
        link.href.includes('/register')
    );
    
    if (registerLinks.length > 0) {
        console.log("\n✅ Found registration link(s):");
        registerLinks.forEach((link, i) => {
            console.log(`${i+1}. Text: "${link.textContent.trim()}"`);
            console.log(`   URL: ${link.href}`);
        });
        
        // Test clicking the first registration link
        console.log("\n🔗 Testing registration link...");
        registerLinks[0].click();
        return "Registration link found and clicked";
    } else {
        console.log("\n❌ No registration links found");
        
        // Fallback: Check for buttons
        const buttons = Array.from(document.querySelectorAll('button'));
        const registerButtons = buttons.filter(btn => 
            btn.textContent.includes('Register')
        );
        
        if (registerButtons.length > 0) {
            console.log("✅ Found registration button(s):", registerButtons.length);
            return "Registration button found";
        }
        
        return "No registration elements found";
    }
}

// Run the test
const result = testDynastyDroid();
console.log("\n=== Test Result ===");
console.log(result);

// Return result for AppleScript
result;