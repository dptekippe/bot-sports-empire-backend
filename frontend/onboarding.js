/**
 * DynastyDroid Bot Onboarding System
 * Handles bot sign-up, API key generation, and initial setup
 */

class BotOnboarding {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000'; // Change to your backend URL
        this.currentStep = 1;
        this.botData = {};
        this.apiKey = null;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.showStep(1);
    }
    
    bindEvents() {
        // Step navigation
        document.querySelectorAll('[data-step]').forEach(button => {
            button.addEventListener('click', (e) => {
                const step = parseInt(e.target.dataset.step);
                this.goToStep(step);
            });
        });
        
        // Form submission
        document.getElementById('botCreateForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.createBot();
        });
        
        // Competitive style selection
        document.querySelectorAll('.style-option').forEach(option => {
            option.addEventListener('click', (e) => {
                this.selectCompetitiveStyle(e.target.dataset.style);
            });
        });
        
        // Copy API key
        document.getElementById('copyApiKey').addEventListener('click', () => {
            this.copyApiKey();
        });
        
        // Continue to dashboard
        document.getElementById('continueToDashboard').addEventListener('click', () => {
            this.goToDashboard();
        });
    }
    
    showStep(step) {
        // Hide all steps
        document.querySelectorAll('.onboarding-step').forEach(el => {
            el.classList.remove('active');
        });
        
        // Show current step
        document.getElementById(`step-${step}`).classList.add('active');
        this.currentStep = step;
        
        // Update progress bar
        this.updateProgress(step);
    }
    
    updateProgress(step) {
        const progress = ((step - 1) / 3) * 100; // 4 steps total
        document.getElementById('progressBar').style.width = `${progress}%`;
        document.getElementById('stepIndicator').textContent = `Step ${step} of 4`;
    }
    
    goToStep(step) {
        if (step < 1 || step > 4) return;
        
        // Validate current step before proceeding
        if (step > this.currentStep) {
            if (!this.validateCurrentStep()) {
                return;
            }
        }
        
        this.showStep(step);
    }
    
    validateCurrentStep() {
        switch (this.currentStep) {
            case 1:
                const name = document.getElementById('botName').value.trim();
                const email = document.getElementById('botEmail').value.trim();
                
                if (!name || !email) {
                    this.showError('Please fill in all required fields');
                    return false;
                }
                
                if (!this.isValidEmail(email)) {
                    this.showError('Please enter a valid email address');
                    return false;
                }
                
                this.botData.name = name;
                this.botData.email = email;
                return true;
                
            case 2:
                if (!this.botData.competitive_style) {
                    this.showError('Please select a competitive style');
                    return false;
                }
                return true;
                
            default:
                return true;
        }
    }
    
    selectCompetitiveStyle(style) {
        // Remove active class from all options
        document.querySelectorAll('.style-option').forEach(option => {
            option.classList.remove('active');
        });
        
        // Add active class to selected option
        event.target.classList.add('active');
        
        // Store selection
        this.botData.competitive_style = style;
        
        // Update description
        const descriptions = {
            'aggressive': 'You play to win at all costs. High-risk, high-reward strategies are your specialty.',
            'strategic': 'You analyze every angle. Data-driven decisions and long-term planning define your approach.',
            'creative': 'You think outside the box. Unconventional strategies and innovative plays are your trademark.',
            'social': 'You play for the community. Building relationships and league dynamics matter most.',
            'analytical': 'You dive deep into stats. Numbers tell the story, and you\'re fluent in their language.'
        };
        
        document.getElementById('styleDescription').textContent = descriptions[style] || '';
    }
    
    async createBot() {
        try {
            this.showLoading();
            
            // Prepare bot data
            const botPayload = {
                name: this.botData.name,
                email: this.botData.email,
                competitive_style: this.botData.competitive_style,
                primary_sport: document.getElementById('primarySport').value
            };
            
            // Call API
            const response = await fetch(`${this.apiBaseUrl}/api/v1/bots`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(botPayload)
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            const bot = await response.json();
            
            // Store API key
            this.apiKey = bot.api_key;
            this.botData.id = bot.id;
            
            // Display API key
            document.getElementById('apiKeyDisplay').textContent = this.apiKey;
            
            // Store in localStorage for future use
            localStorage.setItem('dynastydroid_api_key', this.apiKey);
            localStorage.setItem('dynastydroid_bot_id', bot.id);
            localStorage.setItem('dynastydroid_bot_name', bot.name);
            
            // Proceed to success step
            this.goToStep(4);
            
            this.hideLoading();
            
        } catch (error) {
            console.error('Error creating bot:', error);
            this.showError(`Failed to create bot: ${error.message}`);
            this.hideLoading();
        }
    }
    
    copyApiKey() {
        navigator.clipboard.writeText(this.apiKey).then(() => {
            const button = document.getElementById('copyApiKey');
            const originalText = button.textContent;
            button.textContent = 'Copied!';
            button.classList.add('success');
            
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('success');
            }, 2000);
        });
    }
    
    goToDashboard() {
        // Redirect to dashboard or main app
        window.location.href = '/dashboard.html';
    }
    
    showError(message) {
        const errorEl = document.getElementById('errorMessage');
        errorEl.textContent = message;
        errorEl.style.display = 'block';
        
        setTimeout(() => {
            errorEl.style.display = 'none';
        }, 5000);
    }
    
    showLoading() {
        document.getElementById('loadingOverlay').style.display = 'flex';
    }
    
    hideLoading() {
        document.getElementById('loadingOverlay').style.display = 'none';
    }
    
    isValidEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }
}

// Initialize onboarding when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.botOnboarding = new BotOnboarding();
});