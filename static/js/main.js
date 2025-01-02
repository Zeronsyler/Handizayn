// Sample product data
const products = [
    {
        id: 1,
        name: 'Modern Geometrik Halı',
        price: 2499.99,
        image: '/static/images/modern1.jpg',
        category: 'modern'
    },
    {
        id: 2,
        name: 'Klasik Anadolu Halısı',
        price: 3999.99,
        image: '/static/images/traditional1.jpg',
        category: 'traditional'
    },
    {
        id: 3,
        name: 'El Dokuma Kilim',
        price: 1899.99,
        image: '/static/images/kilim1.jpg',
        category: 'kilim'
    },
    // Add more products as needed
];

// Cart functionality
let cart = [];

function addToCart(productId) {
    const product = products.find(p => p.id === productId);
    if (product) {
        cart.push(product);
        updateCartUI();
        showNotification('Ürün sepete eklendi');
    }
}

function updateCartUI() {
    const cartIcon = document.querySelector('.fa-shopping-cart');
    if (cartIcon) {
        cartIcon.setAttribute('data-count', cart.length);
    }
}

function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Load featured products
function loadFeaturedProducts() {
    const featuredSection = document.querySelector('#featured .row');
    if (featuredSection) {
        products.forEach(product => {
            const productCard = createProductCard(product);
            featuredSection.appendChild(productCard);
        });
    }
}

function createProductCard(product) {
    const col = document.createElement('div');
    col.className = 'col-md-4 mb-4';
    
    col.innerHTML = `
        <div class="card product-card">
            <img src="${product.image}" class="card-img-top" alt="${product.name}">
            <div class="card-body">
                <h5 class="card-title">${product.name}</h5>
                <p class="price">${product.price.toLocaleString('tr-TR')} ₺</p>
                <button onclick="addToCart(${product.id})" class="btn btn-primary">Sepete Ekle</button>
            </div>
        </div>
    `;
    
    return col;
}

// Initialize AOS
AOS.init({
    duration: 800,
    easing: 'ease-in-out',
    once: true,
    mirror: false
});

// Preloader
window.addEventListener('load', () => {
    const preloader = document.getElementById('preloader');
    setTimeout(() => {
        preloader.style.opacity = '0';
        setTimeout(() => {
            preloader.style.display = 'none';
        }, 500);
    }, 1500);
});

// Navbar Scroll Effect
window.addEventListener('scroll', () => {
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > 50) {
        navbar.style.padding = '0.5rem 0';
        navbar.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
    } else {
        navbar.style.padding = '1rem 0';
        navbar.style.boxShadow = 'none';
    }
});

// Back to Top Button
const backToTop = document.getElementById('backToTop');

window.addEventListener('scroll', () => {
    if (window.scrollY > 300) {
        backToTop.classList.add('active');
    } else {
        backToTop.classList.remove('active');
    }
});

backToTop.addEventListener('click', (e) => {
    e.preventDefault();
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
});

// Smooth Scroll for Navigation Links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            const headerOffset = 80;
            const elementPosition = target.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

            window.scrollTo({
                top: offsetPosition,
                behavior: 'smooth'
            });
        }
    });
});

// Category Card Hover Effect
document.querySelectorAll('.category-card').forEach(card => {
    card.addEventListener('mouseenter', () => {
        const overlay = card.querySelector('.category-overlay');
        if (overlay) {
            overlay.style.transform = 'translateY(0)';
        }
    });

    card.addEventListener('mouseleave', () => {
        const overlay = card.querySelector('.category-overlay');
        if (overlay) {
            overlay.style.transform = 'translateY(100%)';
        }
    });
});

// Image Modal
document.querySelectorAll('[data-toggle="modal"]').forEach(button => {
    button.addEventListener('click', () => {
        const target = button.getAttribute('data-target');
        const modal = document.querySelector(target);
        if (modal) {
            const modalImage = modal.querySelector('img');
            const productImage = button.querySelector('img');
            if (modalImage && productImage) {
                modalImage.src = productImage.src;
            }
        }
    });
});

// Form Validation
const forms = document.querySelectorAll('.needs-validation');
forms.forEach(form => {
    form.addEventListener('submit', event => {
        if (!form.checkValidity()) {
            event.preventDefault();
            event.stopPropagation();
        }
        form.classList.add('was-validated');
    });
});

// Parallax Effect for Hero Section
window.addEventListener('scroll', () => {
    const heroImage = document.querySelector('.hero-image');
    if (heroImage) {
        const scrolled = window.pageYOffset;
        heroImage.style.transform = `translate3d(0, ${scrolled * 0.5}px, 0)`;
    }
});

// Initialize Tooltips
const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
});

// Animate products on scroll
const observeProducts = () => {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });

    document.querySelectorAll('.product-card').forEach(card => {
        observer.observe(card);
    });
};

// Product Modal Functions
function showProductDetails(productId) {
    fetch(`/api/products/${productId}`)
        .then(response => response.json())
        .then(product => {
            document.getElementById('modalProductImage').src = `/static/${product.image_path}`;
            document.getElementById('modalProductName').textContent = product.name;
            document.getElementById('modalProductPrice').textContent = `${product.price.toFixed(2)} ₺`;
            document.getElementById('modalProductCategory').textContent = product.category;
            document.getElementById('modalProductDescription').textContent = product.description;
            
            const modal = new bootstrap.Modal(document.getElementById('productModal'));
            modal.show();
        })
        .catch(error => console.error('Error:', error));
}

// Contact Form Submission
document.getElementById('contactForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());
    
    fetch('/api/contact', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            alert('Mesajınız başarıyla gönderildi. En kısa sürede size dönüş yapacağız.');
            this.reset();
        } else {
            alert('Mesajınız gönderilemedi. Lütfen daha sonra tekrar deneyin.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Bir hata oluştu. Lütfen daha sonra tekrar deneyin.');
    });
});

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    observeProducts();
});
