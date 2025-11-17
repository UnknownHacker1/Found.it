/**
 * Login Page Renderer
 * Handles OAuth login flow and session management
 */

const API_URL = 'http://localhost:8001';

// DOM Elements
const loginButton = document.getElementById('loginButton');
const googleLoginBtn = document.getElementById('googleLoginBtn');
const skipButton = document.getElementById('skipButton');
const statusDiv = document.getElementById('status');

// Check if user is already logged in
window.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('auth_token');
    if (token) {
        // Verify token is still valid
        try {
            const response = await fetch(`${API_URL}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                // User is already logged in, redirect to main app
                showStatus('Already logged in! Redirecting...', 'success');
                setTimeout(() => {
                    window.location.href = 'index-chat.html';
                }, 1000);
                return;
            } else {
                // Token is invalid, clear it
                localStorage.removeItem('auth_token');
                localStorage.removeItem('user_info');
            }
        } catch (error) {
            console.error('Token verification failed:', error);
        }
    }

    // Check if OAuth is configured on the backend
    checkOAuthStatus();
});

// Check OAuth configuration status
async function checkOAuthStatus() {
    try {
        const response = await fetch(`${API_URL}/auth/status`);
        const data = await response.json();

        if (!data.oauth_enabled) {
            // OAuth not configured - just disable Google login button
            if (googleLoginBtn) {
                googleLoginBtn.disabled = true;
                googleLoginBtn.style.opacity = '0.5';
                googleLoginBtn.title = 'OAuth not configured on backend';
            }
        }
    } catch (error) {
        console.error('Failed to check OAuth status:', error);
        showStatus('⚠️ Backend offline. Please start the backend server first.', 'error');
    }
}

// Google Login Button Handler (just goes to app like skip button)
if (googleLoginBtn) {
    googleLoginBtn.addEventListener('click', () => {
        // Set a guest session
        localStorage.setItem('guest_mode', 'true');
        showStatus('Logging in...', 'success');

        setTimeout(() => {
            window.location.href = 'index-chat.html';
        }, 500);
    });
}

// Legacy login button handler (if exists)
if (loginButton) {
    loginButton.addEventListener('click', async () => {
        try {
            showStatus('Opening login window...', 'info');

            // Open OAuth login in a new window
            const loginWindow = window.open(
                `${API_URL}/auth/login`,
                'Login',
                'width=500,height=600,left=200,top=100'
            );

            // Poll for the token in the opened window
            const pollTimer = setInterval(() => {
                try {
                    // Check if window has navigated to success page
                    if (loginWindow.location.href.includes('auth/success')) {
                        const hash = loginWindow.location.hash;
                        if (hash.includes('token=')) {
                            const token = hash.split('token=')[1];

                            // Clear the timer
                            clearInterval(pollTimer);

                            // Close the login window
                            loginWindow.close();

                            // Save token and redirect
                            handleLoginSuccess(token);
                        }
                    }

                    // Check if window was closed
                    if (loginWindow.closed) {
                        clearInterval(pollTimer);
                        showStatus('Login cancelled', 'info');
                    }
                } catch (error) {
                    // Cross-origin error is expected while on Google's domain
                    // Silently continue polling
                }
            }, 500);

            // Set a timeout to stop polling after 5 minutes
            setTimeout(() => {
                clearInterval(pollTimer);
                if (!loginWindow.closed) {
                    loginWindow.close();
                }
            }, 5 * 60 * 1000);

        } catch (error) {
            console.error('Login error:', error);
            showStatus('Login failed. Please try again.', 'error');
        }
    });
}

// Skip login button handler
skipButton.addEventListener('click', () => {
    // Set a guest session
    localStorage.setItem('guest_mode', 'true');
    showStatus('Continuing as guest...', 'success');

    setTimeout(() => {
        window.location.href = 'index-chat.html';
    }, 500);
});

// Handle successful login
async function handleLoginSuccess(token) {
    try {
        // Store the token
        localStorage.setItem('auth_token', token);

        // Fetch user info
        const response = await fetch(`${API_URL}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const userInfo = await response.json();
            localStorage.setItem('user_info', JSON.stringify(userInfo));

            showStatus(`Welcome, ${userInfo.name}!`, 'success');

            // Redirect to main app
            setTimeout(() => {
                window.location.href = 'index-chat.html';
            }, 1000);
        } else {
            throw new Error('Failed to fetch user info');
        }
    } catch (error) {
        console.error('Error handling login:', error);
        showStatus('Login succeeded but failed to fetch user info', 'error');
    }
}

// Show status message
function showStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = `status-message ${type}`;
    statusDiv.style.display = 'block';

    // Auto-hide after 5 seconds for non-error messages
    if (type !== 'error') {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 5000);
    }
}

// Utility: Get current user from localStorage
function getCurrentUser() {
    const userInfo = localStorage.getItem('user_info');
    return userInfo ? JSON.parse(userInfo) : null;
}

// Utility: Check if user is authenticated
function isAuthenticated() {
    return !!localStorage.getItem('auth_token');
}

// Utility: Logout
function logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_info');
    localStorage.removeItem('guest_mode');
    window.location.href = 'login.html';
}

// Export utilities for use in other pages
window.authUtils = {
    getCurrentUser,
    isAuthenticated,
    logout,
    getToken: () => localStorage.getItem('auth_token')
};
