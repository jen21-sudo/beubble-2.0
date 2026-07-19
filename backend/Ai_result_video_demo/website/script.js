// ============================================
// Beubble 2.0 - Cereal & Rare Earth Materials
// Website Prototype - JavaScript
// ============================================

// --- DOM Ready ---
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initHeroAnimation();
    initPriceTicker();
    initScrollAnimations();
    initContactForm();
    initMarketCharts();
    initDarkMode();
    initMobileMenu();
});

// ============================================
// NAVIGATION
// ============================================
function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    const header = document.querySelector('.header');

    // Smooth scroll for anchor links
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href');
            const targetSection = document.querySelector(targetId);
            if (targetSection) {
                targetSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
            // Update active state
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
        });
    });

    // Header scroll effect
    let lastScroll = 0;
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        if (currentScroll > 100) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
        lastScroll = currentScroll;
    });

    // Active section detection on scroll
    const sections = document.querySelectorAll('section[id]');
    window.addEventListener('scroll', () => {
        const scrollY = window.pageYOffset;
        sections.forEach(section => {
            const sectionHeight = section.offsetHeight;
            const sectionTop = section.offsetTop - 150;
            const sectionId = section.getAttribute('id');
            if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) {
                navLinks.forEach(link => {
                    link.classList.remove('active');
                    if (link.getAttribute('href') === `#${sectionId}`) {
                        link.classList.add('active');
                    }
                });
            }
        });
    });
}

// ============================================
// MOBILE MENU
// ============================================
function initMobileMenu() {
    const menuToggle = document.querySelector('.menu-toggle');
    const navMenu = document.querySelector('.nav-menu');

    if (menuToggle && navMenu) {
        menuToggle.addEventListener('click', () => {
            navMenu.classList.toggle('open');
            menuToggle.classList.toggle('active');
            const isExpanded = navMenu.classList.contains('open');
            menuToggle.setAttribute('aria-expanded', isExpanded);
        });

        // Close menu on link click (mobile)
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                navMenu.classList.remove('open');
                menuToggle.classList.remove('active');
            });
        });
    }
}

// ============================================
// HERO ANIMATION
// ============================================
function initHeroAnimation() {
    const hero = document.querySelector('.hero');
    if (!hero) return;

    // Create floating particles
    const particleCount = 30;
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.classList.add('particle');
        particle.style.left = `${Math.random() * 100}%`;
        particle.style.top = `${Math.random() * 100}%`;
        particle.style.animationDelay = `${Math.random() * 5}s`;
        particle.style.animationDuration = `${3 + Math.random() * 4}s`;
        particle.style.width = `${2 + Math.random() * 6}px`;
        particle.style.height = particle.style.width;
        particle.style.opacity = `${0.2 + Math.random() * 0.5}`;
        hero.appendChild(particle);
    }

    // Typewriter effect for hero subtitle
    const typewriterEl = document.querySelector('.hero-subtitle');
    if (typewriterEl) {
        const text = typewriterEl.textContent;
        typewriterEl.textContent = '';
        let charIndex = 0;
        function typeChar() {
            if (charIndex < text.length) {
                typewriterEl.textContent += text.charAt(charIndex);
                charIndex++;
                setTimeout(typeChar, 40);
            }
        }
        setTimeout(typeChar, 800);
    }
}

// ============================================
// PRICE TICKER
// ============================================
function initPriceTicker() {
    const tickerContainer = document.querySelector('.price-ticker');
    if (!tickerContainer) return;

    const commodities = [
        { name: 'Wheat (CBOT)', price: 6.42, change: +0.12, unit: 'USD/bu' },
        { name: 'Corn (CBOT)', price: 4.85, change: -0.05, unit: 'USD/bu' },
        { name: 'Rice (CBOT)', price: 17.20, change: +0.35, unit: 'USD/cwt' },
        { name: 'Neodymium', price: 72.50, change: +1.20, unit: 'USD/kg' },
        { name: 'Praseodymium', price: 68.00, change: +0.85, unit: 'USD/kg' },
        { name: 'Terbium', price: 850.00, change: -12.50, unit: 'USD/kg' },
        { name: 'Dysprosium', price: 285.00, change: +3.40, unit: 'USD/kg' },
        { name: 'Barley', price: 5.10, change: +0.08, unit: 'USD/bu' },
        { name: 'Oats', price: 3.95, change: -0.03, unit: 'USD/bu' },
        { name: 'Europium', price: 42.00, change: +0.55, unit: 'USD/kg' }
    ];

    function renderTicker() {
        tickerContainer.innerHTML = '';
        const track = document.createElement('div');
        track.classList.add('ticker-track');

        // Duplicate for seamless loop
        const allItems = [...commodities, ...commodities];
        allItems.forEach(item => {
            const el = document.createElement('div');
            el.classList.add('ticker-item');
            const changeClass = item.change >= 0 ? 'positive' : 'negative';
            const arrow = item.change >= 0 ? '▲' : '▼';
            el.innerHTML = `
                <span class="ticker-name">${item.name}</span>
                <span class="ticker-price">${item.price.toFixed(2)} ${item.unit}</span>
                <span class="ticker-change ${changeClass}">${arrow} ${Math.abs(item.change).toFixed(2)}</span>
            `;
            track.appendChild(el);
        });

        tickerContainer.appendChild(track);
    }

    renderTicker();

    // Simulate live price updates every 5 seconds
    setInterval(() => {
        commodities.forEach(item => {
            const fluctuation = (Math.random() - 0.5) * 0.1;
            item.price = Math.max(0.01, item.price + fluctuation);
            item.change = fluctuation;
        });
        renderTicker();
    }, 5000);
}

// ============================================
// SCROLL ANIMATIONS
// ============================================
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    const animatedElements = document.querySelectorAll('.animate-on-scroll');
    animatedElements.forEach(el => observer.observe(el));
}

// ============================================
// MARKET CHARTS (Canvas-based)
// ============================================
function initMarketCharts() {
    const chartCanvases = document.querySelectorAll('.market-chart');
    chartCanvases.forEach(canvas => {
        const ctx = canvas.getContext('2d');
        const chartType = canvas.dataset.type;
        const chartData = canvas.dataset.values ? JSON.parse(canvas.dataset.values) : null;

        if (chartType === 'line' && chartData) {
            drawLineChart(ctx, canvas, chartData);
        } else if (chartType === 'bar' && chartData) {
            drawBarChart(ctx, canvas, chartData);
        } else {
            drawDefaultChart(ctx, canvas);
        }
    });
}

function drawLineChart(ctx, canvas, data) {
    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    ctx.clearRect(0, 0, width, height);

    const values = data.values || [65, 72, 68, 80, 75, 90, 85, 95, 88, 100, 92, 105];
    const labels = data.labels || ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const maxVal = Math.max(...values) * 1.1;
    const minVal = Math.min(...values) * 0.9;
    const range = maxVal - minVal;

    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.1)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padding + (chartHeight / 4) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();

        // Y-axis labels
        const val = maxVal - (range / 4) * i;
        ctx.fillStyle = 'rgba(255,255,255,0.6)';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText(val.toFixed(1), padding - 5, y + 4);
    }

    // X-axis labels
    ctx.textAlign = 'center';
    values.forEach((_, i) => {
        const x = padding + (chartWidth / (values.length - 1)) * i;
        ctx.fillStyle = 'rgba(255,255,255,0.6)';
        ctx.fillText(labels[i] || '', x, height - 10);
    });

    // Gradient fill
    const gradient = ctx.createLinearGradient(0, padding, 0, height - padding);
    gradient.addColorStop(0, 'rgba(0, 200, 150, 0.3)');
    gradient.addColorStop(1, 'rgba(0, 200, 150, 0.0)');

    // Draw fill
    ctx.beginPath();
    ctx.moveTo(padding, height - padding);
    values.forEach((val, i) => {
        const x = padding + (chartWidth / (values.length - 1)) * i;
        const y = padding + chartHeight - ((val - minVal) / range) * chartHeight;
        ctx.lineTo(x, y);
    });
    ctx.lineTo(padding + chartWidth, height - padding);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Draw line
    ctx.beginPath();
    ctx.strokeStyle = '#00c896';
    ctx.lineWidth = 2.5;
    ctx.lineJoin = 'round';
    values.forEach((val, i) => {
        const x = padding + (chartWidth / (values.length - 1)) * i;
        const y = padding + chartHeight - ((val - minVal) / range) * chartHeight;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Draw dots
    values.forEach((val, i) => {
        const x = padding + (chartWidth / (values.length - 1)) * i;
        const y = padding + chartHeight - ((val - minVal) / range) * chartHeight;
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#00c896';
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1.5;
        ctx.stroke();
    });
}

function drawBarChart(ctx, canvas, data) {
    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    ctx.clearRect(0, 0, width, height);

    const values = data.values || [45, 62, 38, 75, 55, 80];
    const labels = data.labels || ['Nd', 'Pr', 'Tb', 'Dy', 'Eu', 'Sm'];
    const maxVal = Math.max(...values) * 1.15;
    const barWidth = (chartWidth / values.length) * 0.6;
    const barGap = (chartWidth / values.length) * 0.4;

    const colors = ['#00c896', '#00a8ff', '#ff6b6b', '#ffd93d', '#c084fc', '#fb923c'];

    // Grid
    ctx.strokeStyle = 'rgba(255,255,255,0.1)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padding + (chartHeight / 4) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
    }

    // Bars
    values.forEach((val, i) => {
        const barHeight = (val / maxVal) * chartHeight;
        const x = padding + (chartWidth / values.length) * i + barGap / 2;
        const y = padding + chartHeight - barHeight;

        // Bar gradient
        const barGradient = ctx.createLinearGradient(x, y, x, y + barHeight);
        barGradient.addColorStop(0, colors[i % colors.length]);
        barGradient.addColorStop(1, colors[i % colors.length] + '66');

        ctx.fillStyle = barGradient;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, [4, 4, 0, 0]);
        ctx.fill();

        // Label
        ctx.fillStyle = 'rgba(255,255,255,0.7)';
        ctx.font = '11px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(labels[i], x + barWidth / 2, height - 10);

        // Value on top
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 10px sans-serif';
        ctx.fillText(val.toFixed(0), x + barWidth / 2, y - 8);
    });
}

function drawDefaultChart(ctx, canvas) {
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = 'rgba(255,255,255,0.3)';
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Chart Data Loading...', width / 2, height / 2);
}

// ============================================
// CONTACT FORM
// ============================================
function initContactForm() {
    const form = document.querySelector('.contact-form');
    if (!form) return;

    form.addEventListener('submit', (e) => {
        e.preventDefault();

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // Basic validation
        let isValid = true;
        form.querySelectorAll('[required]').forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('error');
                isValid = false;
            } else {
                field.classList.remove('error');
            }
        });

        // Email validation
        const emailField = form.querySelector('input[type="email"]');
        if (emailField && emailField.value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(emailField.value)) {
                emailField.classList.add('error');
                isValid = false;
            }
        }

        if (isValid) {
            // Simulate form submission
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Sending...';
            submitBtn.disabled = true;

            setTimeout(() => {
                submitBtn.textContent = '✓ Message Sent!';
                submitBtn.classList.add('success');
                form.reset();

                setTimeout(() => {
                    submitBtn.textContent = originalText;
                    submitBtn.disabled = false;
                    submitBtn.classList.remove('success');
                }, 3000);
            }, 1500);
        }
    });

    // Remove error on input
    form.querySelectorAll('input, textarea, select').forEach(field => {
        field.addEventListener('input', () => {
            field.classList.remove('error');
        });
    });
}

// ============================================
// DARK MODE TOGGLE
// ============================================
function initDarkMode() {
    const toggle = document.querySelector('.dark-mode-toggle');
    if (!toggle) return;

    // Check saved preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        document.body.classList.remove('dark-mode');
    }

    toggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDark = !document.body.classList.contains('dark-mode');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    });
}

// ============================================
// UTILITY: Counter Animation
// ============================================
function animateCounter(element, target, duration = 2000) {
    const start = 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
        const current = Math.floor(start + (target - start) * eased);
        element.textContent = current.toLocaleString();
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

// ============================================
// UTILITY: Debounce
// ============================================
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ============================================
// MARKET DATA FETCHER (API Integration Ready)
// ============================================
class MarketDataFetcher {
    constructor() {
        this.baseURL = '/api/v1';
        this.cache = new Map();
        this.cacheTimeout = 60000; // 1 minute
    }

    async fetchPrices(market = 'all') {
        const cacheKey = `prices_${market}`;
        const cached = this.cache.get(cacheKey);

        if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
            return cached.data;
        }

        try {
            // Simulated API call - replace with real endpoint
            const response = await this.simulateAPI('/prices', { market });
            this.cache.set(cacheKey, { data: response, timestamp: Date.now() });
            return response;
        } catch (error) {
            console.error('Failed to fetch market prices:', error);
            return null;
        }
    }

    async fetchForecast(commodity, period = '12m') {
        try {
            const response = await this.simulateAPI('/forecast', { commodity, period });
            return response;
        } catch (error) {
            console.error('Failed to fetch forecast:', error);
            return null;
        }
    }

    async simulateAPI(endpoint, params) {
        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 300 + Math.random() * 500));

        // Return mock data
        return {
            status: 'success',
            timestamp: new Date().toISOString(),
            data: {
                cereals: {
                    wheat: { price: 6.42, change: 0.12, trend: 'up' },
                    corn: { price: 4.85, change: -0.05, trend: 'down' },
                    rice: { price: 17.20, change: 0.35, trend: 'up' },
                    barley: { price: 5.10, change: 0.08, trend: 'up' }
                },
                rareEarths: {
                    neodymium: { price: 72.50, change: 1.20, trend: 'up' },
                    praseodymium: { price: 68.00, change: 0.85, trend: 'up' },
                    terbium: { price: 850.00, change: -12.50, trend: 'down' },
                    dysprosium: { price: 285.00, change: 3.40, trend: 'up' }
                }
            }
        };
    }
}

// Initialize market data fetcher
const marketData = new MarketDataFetcher();

// ============================================
// NOTIFICATION SYSTEM
// ============================================
class NotificationManager {
    constructor() {
        this.container = document.querySelector('.notification-container') || this.createContainer();
    }

    createContainer() {
        const container = document.createElement('div');
        container.classList.add('notification-container');
        container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:10000;display:flex;flex-direction:column;gap:10px;';
        document.body.appendChild(container);
        return container;
    }

    show(message, type = 'info', duration = 4000) {
        const notification = document.createElement('div');
        notification.classList.add('notification', `notification-${type}`);
        notification.innerHTML = `
            <span class="notification-icon">${this.getIcon(type)}</span>
            <span class="notification-message">${message}</span>
            <button class="notification-close">&times;</button>
        `;

        notification.style.cssText = `
            background: ${this.getColor(type)};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            animation: slideIn 0.3s ease;
            min-width: 300px;
        `;

        notification.querySelector('.notification-close').addEventListener('click', () => {
            this.dismiss(notification);
        });

        this.container.appendChild(notification);

        if (duration > 0) {
            setTimeout(() => this.dismiss(notification), duration);
        }
    }

    dismiss(notification) {
        notification.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => notification.remove(), 300);
    }

    getIcon(type) {
        const icons = { info: 'ℹ️', success: '✅', warning: '⚠️', error: '❌' };
        return icons[type] || icons.info;
    }

    getColor(type) {
        const colors = {
            info: 'linear-gradient(135deg, #00a8ff, #0077b6)',
            success: 'linear-gradient(135deg, #00c896, #00875a)',
            warning: 'linear-gradient(135deg, #ffd93d, #f59e0b)',
            error: 'linear-gradient(135deg, #ff6b6b, #dc2626)'
        };
        return colors[type] || colors.info;
    }
}

const notifications = new NotificationManager();

// ============================================
// PRICE ALERT SYSTEM
// ============================================
class PriceAlertSystem {
    constructor() {
        this.alerts = [];
        this.thresholds = {};
    }

    setAlert(commodity, threshold, direction = 'above') {
        this.alerts.push({ commodity, threshold, direction, triggered: false });
    }

    checkPrices(prices) {
        this.alerts.forEach(alert => {
            const currentPrice = prices[alert.commodity];
            if (!currentPrice || alert.triggered) return;

            const shouldTrigger = alert.direction === 'above'
                ? currentPrice >= alert.threshold
                : currentPrice <= alert.threshold;

            if (shouldTrigger) {
                alert.triggered = true;
                notifications.show(
                    `Price Alert: ${alert.commodity} is ${alert.direction} ${alert.threshold}!`,
                    'warning'
                );
            }
        });
    }
}

const priceAlerts = new PriceAlertSystem();

// ============================================
// EXPORT FOR MODULE USAGE
// ============================================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        MarketDataFetcher,
        NotificationManager,
        PriceAlertSystem,
        animateCounter,
        debounce
    };
}

console.log('%c🌾 Beubble 2.0 - Cereal & Rare Earth Materials Platform', 'color: #00c896; font-size: 16px; font-weight: bold;');
console.log('%cMarket Intelligence System Initialized', 'color: #00a8ff; font-size: 12px;');
