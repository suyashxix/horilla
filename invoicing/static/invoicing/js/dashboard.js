/**
 * Dashboard Management JavaScript
 * Handles dashboard interactions and real-time updates
 */

class DashboardManager {
    constructor() {
        this.refreshInterval = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeAnimations();
        this.startAutoRefresh();
        console.log('Dashboard Manager initialized');
    }

    bindEvents() {
        // Refresh button functionality
        const refreshBtn = document.getElementById('refreshDashboard');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshDashboard());
        }

        // Card hover effects
        this.initializeCardHovers();

        // Quick action buttons
        this.initializeQuickActions();

        // Statistics animation on scroll
        this.initializeCounterAnimation();
    }

    initializeAnimations() {
        // Add fade-in animation to cards
        const cards = document.querySelectorAll('.oh-card-dashboard, .oh-card');
        cards.forEach((card, index) => {
            card.style.animationDelay = `${index * 0.1}s`;
            card.classList.add('fade-in');
        });

        // Animate statistics numbers
        this.animateCounters();
    }

    initializeCardHovers() {
        const dashboardCards = document.querySelectorAll('.oh-card-dashboard');
        
        dashboardCards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-4px)';
                card.style.boxShadow = '0 8px 25px rgba(0, 0, 0, 0.15)';
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0)';
                card.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.05)';
            });
        });
    }

    initializeQuickActions() {
        const quickActionBtns = document.querySelectorAll('.oh-btn');
        
        quickActionBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                // Add click animation
                btn.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    btn.style.transform = '';
                }, 150);
            });
        });
    }

    animateCounters() {
        const counters = document.querySelectorAll('.oh-stats__number');
        
        counters.forEach(counter => {
            const target = parseInt(counter.textContent);
            const duration = 1000; // 1 second
            const step = target / (duration / 16); // 60fps
            let current = 0;

            const timer = setInterval(() => {
                current += step;
                if (current >= target) {
                    current = target;
                    clearInterval(timer);
                }
                counter.textContent = Math.floor(current);
            }, 16);
        });
    }

    initializeCounterAnimation() {
        // Intersection Observer for counter animation on scroll
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const counter = entry.target.querySelector('.oh-stats__number');
                    if (counter && !counter.classList.contains('animated')) {
                        counter.classList.add('animated');
                        this.animateCounter(counter);
                    }
                }
            });
        });

        document.querySelectorAll('.oh-card-dashboard').forEach(card => {
            observer.observe(card);
        });
    }

    animateCounter(element) {
        const target = parseInt(element.textContent);
        const duration = 1500;
        const step = target / (duration / 16);
        let current = 0;

        element.textContent = '0';

        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current);
        }, 16);
    }

    async refreshDashboard() {
        const refreshBtn = document.getElementById('refreshDashboard');
        if (refreshBtn) {
            refreshBtn.classList.add('loading');
        }

        try {
            // Simulate refresh (you can implement actual AJAX call here)
            await this.sleep(1000);
            
            // Update timestamp
            const timestamp = document.getElementById('lastUpdated');
            if (timestamp) {
                timestamp.textContent = new Date().toLocaleTimeString();
            }

            this.showToast('Dashboard refreshed successfully', 'success');
        } catch (error) {
            console.error('Error refreshing dashboard:', error);
            this.showToast('Error refreshing dashboard', 'error');
        } finally {
            if (refreshBtn) {
                refreshBtn.classList.remove('loading');
            }
        }
    }

    startAutoRefresh() {
        // Auto-refresh every 5 minutes
        this.refreshInterval = setInterval(() => {
            this.refreshDashboard();
        }, 300000); // 5 minutes
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast--${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#007bff'};
            color: white;
            border-radius: 8px;
            z-index: 9999;
            animation: slideIn 0.3s ease;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Real-time updates (if you implement WebSocket)
    initializeRealTimeUpdates() {
        // Example WebSocket connection
        // const ws = new WebSocket('ws://localhost:8000/ws/dashboard/');
        // ws.onmessage = (event) => {
        //     const data = JSON.parse(event.data);
        //     this.updateDashboardData(data);
        // };
    }

    updateDashboardData(data) {
        // Update dashboard with real-time data
        if (data.stats) {
            Object.keys(data.stats).forEach(key => {
                const element = document.querySelector(`[data-stat="${key}"]`);
                if (element) {
                    this.animateCounter(element);
                }
            });
        }
    }

    // Cleanup when leaving page
    destroy() {
        this.stopAutoRefresh();
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardManager = new DashboardManager();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboardManager) {
        window.dashboardManager.destroy();
    }
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    .pulse {
        animation: pulse 2s infinite;
    }
`;
document.head.appendChild(style);
