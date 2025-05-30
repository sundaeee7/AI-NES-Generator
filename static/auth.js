const firebaseConfig = {
    apiKey: "AIzaSyCxCTWeDMGByvensJ0ALyFkl22cPlyU1f0",
    authDomain: "chipgen-9465b.firebaseapp.com",
    projectId: "chipgen-9465b",
    storageBucket: "chipgen-9465b.firebasestorage.app",
    messagingSenderId: "95781012079",
    appId: "1:95781012079:web:f742b96ea2daf0d52ec39a",
    measurementId: "G-Z8W8YXT5FH"
};

firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
const db = firebase.firestore();

function register() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    if (!email || !password) {
        alert('Пожалуйста, введите email и пароль');
        return;
    }
    if (password.length < 6) {
        alert('Пароль должен быть не менее 6 символов');
        return;
    }

    auth.createUserWithEmailAndPassword(email, password)
        .then((userCredential) => {
            const user = userCredential.user;
            return db.collection('users').doc(user.uid).set({
                email: email,
                createdAt: firebase.firestore.FieldValue.serverTimestamp()
            });
        })
        .then(() => {
            alert('Регистрация успешна!');
            window.location.href = '/';
        })
        .catch((error) => {
            console.error('Ошибка регистрации:', error);
            alert('Ошибка: ' + error.message);
        });
}

function login() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    if (!email || !password) {
        alert('Пожалуйста, введите email и пароль');
        return;
    }

    auth.signInWithEmailAndPassword(email, password)
        .then((userCredential) => {
            alert('Вход успешен!');
            window.location.href = '/';
        })
        .catch((error) => {
            console.error('Ошибка входа:', error);
            alert('Ошибка: ' + error.message);
        });
}

function logout() {
    auth.signOut()
        .then(() => {
            alert('Вы вышли из аккаунта');
            window.location.href = '/auth';
        })
        .catch((error) => {
            console.error('Ошибка выхода:', error);
            alert('Ошибка: ' + error.message);
        });
}

auth.onAuthStateChanged((user) => {
    console.log('Auth state changed:', user ? user.email : 'No user');
    const authSection = document.getElementById('auth-section');
    const logoutButton = document.getElementById('logoutButton');
    const navbarLogoutButton = document.getElementById('navbarLogoutButton');
    const userInfo = document.getElementById('user-info');
    const userEmail = document.getElementById('user-email');

    if (user) {
        if (authSection) authSection.style.display = 'none';
        if (logoutButton) logoutButton.style.display = 'inline-block';
        if (navbarLogoutButton) navbarLogoutButton.style.display = 'inline-block';
        if (userInfo) userInfo.style.display = 'block';
        if (userEmail) userEmail.textContent = user.email;
    } else {
        if (authSection) authSection.style.display = 'block';
        if (logoutButton) logoutButton.style.display = 'none';
        if (navbarLogoutButton) navbarLogoutButton.style.display = 'none';
        if (userInfo) userInfo.style.display = 'none';
        if (window.location.pathname === '/history') {
            window.location.href = '/auth';
        }
    }
});

const originalFetch = window.fetch;
window.fetch = async function(resource, options = {}) {
    console.log('Intercepted fetch to:', resource);
    const user = firebase.auth().currentUser;
    if (user) {
        const token = await user.getIdToken();
        console.log('Adding token to headers:', token);
        options.headers = {
            ...options.headers,
            'Authorization': `Bearer ${token}`
        };
    } else {
        console.log('No user logged in, skipping token');
    }
    return originalFetch(resource, options);
};

document.addEventListener('DOMContentLoaded', () => {
    const registerButton = document.getElementById('registerButton');
    const loginButton = document.getElementById('loginButton');
    const logoutButton = document.getElementById('logoutButton');
    const navbarLogoutButton = document.getElementById('navbarLogoutButton');

    if (registerButton) registerButton.addEventListener('click', register);
    if (loginButton) loginButton.addEventListener('click', login);
    if (logoutButton) logoutButton.addEventListener('click', logout);
    if (navbarLogoutButton) navbarLogoutButton.addEventListener('click', logout);
});