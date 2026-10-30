document.documentElement.classList.add('js');

// Mobile menu
const toggle = document.querySelector('.nav-toggle');
const nav = document.getElementById('nav');

toggle.addEventListener('click', () => {
  const open = nav.classList.toggle('is-open');
  toggle.setAttribute('aria-expanded', String(open));
});

nav.addEventListener('click', (e) => {
  if (e.target.tagName === 'A') {
    nav.classList.remove('is-open');
    toggle.setAttribute('aria-expanded', 'false');
  }
});

// Dropdowns: hover on desktop, tap to expand in the mobile menu
nav.querySelectorAll('.nav-sub-toggle').forEach((btn) => {
  btn.addEventListener('click', () => {
    const item = btn.closest('.nav-item');
    const open = !item.classList.contains('is-open');
    nav.querySelectorAll('.nav-item.is-open').forEach((el) => {
      el.classList.remove('is-open');
      el.querySelector('.nav-sub-toggle').setAttribute('aria-expanded', 'false');
    });
    item.classList.toggle('is-open', open);
    btn.setAttribute('aria-expanded', String(open));
  });
});

document.addEventListener('click', (e) => {
  if (e.target.closest('.nav-item')) return;
  nav.querySelectorAll('.nav-item.is-open').forEach((el) => {
    el.classList.remove('is-open');
    el.querySelector('.nav-sub-toggle').setAttribute('aria-expanded', 'false');
  });
});

// Header shadow and "to top" button
const header = document.querySelector('.site-header');
const toTop = document.querySelector('.to-top');

const onScroll = () => {
  header.classList.toggle('is-scrolled', window.scrollY > 10);
  toTop.classList.toggle('is-visible', window.scrollY > 600);
};
window.addEventListener('scroll', onScroll, { passive: true });
onScroll();
toTop.addEventListener('click', () => window.scrollTo({ top: 0 }));

// Reveal on scroll
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('is-visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });

document.querySelectorAll('.reveal').forEach((el) => revealObserver.observe(el));

// Highlight the nav link of the section in view
const links = [...nav.querySelectorAll('a[href^="#"]')];
const targets = links.map((a) => document.querySelector(a.getAttribute('href'))).filter(Boolean);

const navObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (!entry.isIntersecting) return;
    links.forEach((a) => a.classList.toggle('is-active', a.getAttribute('href') === '#' + entry.target.id));
  });
}, { rootMargin: '-45% 0px -50% 0px' });

targets.forEach((t) => navObserver.observe(t));

// Reviews slider (only on pages that have one)
const slider = document.querySelector('[data-slider]');
if (slider) {
  const track = slider.querySelector('.slider-track');
  const slides = [...track.children];
  const dotsBox = slider.querySelector('.slider-dots');
  let current = 0;

  const perView = () => (window.innerWidth > 1024 ? 2 : 1);
  const pages = () => Math.ceil(slides.length / perView());

  const renderDots = () => {
    dotsBox.innerHTML = '';
    for (let i = 0; i < pages(); i++) {
      const dot = document.createElement('button');
      dot.setAttribute('aria-label', `Отзывы, страница ${i + 1}`);
      dot.addEventListener('click', () => goTo(i));
      dotsBox.append(dot);
    }
  };

  const goTo = (i) => {
    current = (i + pages()) % pages();
    track.style.transform = `translateX(-${current * 100}%)`;
    [...dotsBox.children].forEach((d, n) => d.classList.toggle('is-active', n === current));
  };

  slider.querySelector('.slider-btn--prev').addEventListener('click', () => goTo(current - 1));
  slider.querySelector('.slider-btn--next').addEventListener('click', () => goTo(current + 1));

  let autoplay = setInterval(() => goTo(current + 1), 7000);
  slider.addEventListener('mouseenter', () => clearInterval(autoplay));
  slider.addEventListener('mouseleave', () => { autoplay = setInterval(() => goTo(current + 1), 7000); });

  let touchX = null;
  track.addEventListener('touchstart', (e) => { touchX = e.touches[0].clientX; }, { passive: true });
  track.addEventListener('touchend', (e) => {
    if (touchX === null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 40) goTo(current + (dx < 0 ? 1 : -1));
    touchX = null;
  });

  window.addEventListener('resize', () => { renderDots(); goTo(Math.min(current, pages() - 1)); });
  renderDots();
  goTo(0);
}

// Links to the full list of works open the collapsed list
const worklist = document.getElementById('price-list');
if (worklist) {
  const openWorklist = () => { if (location.hash === '#price-list') worklist.open = true; };
  document.querySelectorAll('a[href="#price-list"]').forEach((a) => a.addEventListener('click', () => { worklist.open = true; }));
  window.addEventListener('hashchange', openWorklist);
  openWorklist();
}

// Modal
const modal = document.querySelector('[data-modal]');
let lastFocus = null;

const openModal = () => {
  lastFocus = document.activeElement;
  modal.hidden = false;
  document.body.style.overflow = 'hidden';
  modal.querySelector('input').focus();
};
const closeModal = () => {
  modal.hidden = true;
  document.body.style.overflow = '';
  if (lastFocus) lastFocus.focus();
};

document.querySelectorAll('[data-modal-open]').forEach((btn) => btn.addEventListener('click', openModal));
modal.querySelectorAll('[data-modal-close]').forEach((el) => el.addEventListener('click', closeModal));
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !modal.hidden) closeModal(); });

// Floating contact button
const fab = document.querySelector('[data-fab]');
const fabBtn = fab.querySelector('.fab-btn');
fabBtn.addEventListener('click', () => {
  const open = fab.classList.toggle('is-open');
  fabBtn.setAttribute('aria-expanded', String(open));
});
document.addEventListener('click', (e) => {
  if (!fab.contains(e.target)) {
    fab.classList.remove('is-open');
    fabBtn.setAttribute('aria-expanded', 'false');
  }
});

// Forms go to Telegram through a Google Apps Script web app (tools/telegram-form.gs),
// which keeps the bot token out of the site code. Paste the web app URL here.
const FORM_ENDPOINT = 'https://script.google.com/macros/s/AKfycbzm-iBhFTimrY7GBatc1zOmu_CwnUCYm7hoh7avEzT_3vsloBmOfe0hlMdW3xhhaQSh/exec';

document.querySelectorAll('[data-form]').forEach((form) => {
  const status = form.querySelector('.form-status');

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    let valid = true;

    form.querySelectorAll('[required]').forEach((field) => {
      const ok = field.type === 'checkbox' ? field.checked
        : field.type === 'tel' ? field.value.replace(/\D/g, '').length >= 9
        : field.value.trim() !== '';
      const target = field.type === 'checkbox' ? field.closest('label') : field;
      target.classList.toggle('is-invalid', !ok);
      if (!ok) valid = false;
    });

    const email = form.querySelector('[type="email"]');
    if (email && email.value && !email.checkValidity()) {
      email.classList.add('is-invalid');
      valid = false;
    }

    status.classList.toggle('is-error', !valid);
    if (!valid) {
      status.textContent = 'Проверьте, пожалуйста, выделенные поля';
      return;
    }

    if (!FORM_ENDPOINT) {
      status.classList.add('is-error');
      status.textContent = 'Форма пока не подключена — позвоните или напишите нам в Telegram.';
      return;
    }

    const data = new URLSearchParams(new FormData(form));
    data.set('form', form.querySelector('h2')?.textContent.trim() || '');
    data.set('page', location.href);
    const button = form.querySelector('[type="submit"]');
    button.disabled = true;
    status.textContent = 'Отправляем…';
    // no-cors: the web app answers from another origin, so the reply can't be read; a network
    // failure still rejects
    fetch(FORM_ENDPOINT, { method: 'POST', mode: 'no-cors', body: data })
      .then(() => {
        status.textContent = 'Спасибо! Заявка отправлена, мы скоро свяжемся с вами.';
        form.reset();
      })
      .catch(() => {
        status.classList.add('is-error');
        status.textContent = 'Не удалось отправить заявку. Проверьте интернет или позвоните нам.';
      })
      .finally(() => { button.disabled = false; });
  });

  form.addEventListener('input', (e) => {
    e.target.classList.remove('is-invalid');
    e.target.closest('label')?.classList.remove('is-invalid');
  });
});
