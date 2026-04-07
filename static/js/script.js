(() => {
  const header = document.querySelector('.header');
  if (!header) {
    return;
  }

  let lastY = window.scrollY;
  let ticking = false;
  const topThreshold = 80;
  const movementThreshold = 6;

  const updateHeader = () => {
    const currentY = window.scrollY;
    const delta = currentY - lastY;

    if (header.classList.contains('menu-open')) {
      header.classList.remove('header--hidden');
      lastY = currentY;
      ticking = false;
      return;
    }

    if (currentY <= topThreshold) {
      header.classList.remove('header--hidden');
    } else if (delta > movementThreshold) {
      header.classList.add('header--hidden');
    } else if (delta < -movementThreshold) {
      header.classList.remove('header--hidden');
    }

    lastY = currentY;
    ticking = false;
  };

  window.addEventListener('scroll', () => {
    if (!ticking) {
      window.requestAnimationFrame(updateHeader);
      ticking = true;
    }
  }, { passive: true });
})();

(() => {
  const targets = document.querySelectorAll('.pick-up');
  if (!targets.length) {
    return;
  }

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) {
    targets.forEach((target) => target.classList.add('section-reveal', 'is-visible'));
    return;
  }

  targets.forEach((target) => target.classList.add('section-reveal'));

  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) {
        return;
      }

      entry.target.classList.add('is-visible');
      obs.unobserve(entry.target);
    });
  }, {
    threshold: 0.15,
    rootMargin: '0px 0px -10% 0px'
  });

  targets.forEach((target) => observer.observe(target));
})();

(() => {
  const header = document.querySelector('.header');
  if (!header) {
    return;
  }

  const setHeaderOffset = () => {
    const height = Math.ceil(header.getBoundingClientRect().height);
    document.documentElement.style.setProperty('--header-offset', `${height + 24}px`);
  };

  setHeaderOffset();
  window.addEventListener('load', setHeaderOffset);
  window.addEventListener('resize', setHeaderOffset);
})();

(() => {
  const header = document.querySelector('.header');
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.header-nav');

  if (!header || !toggle || !nav) {
    return;
  }

  const mobileMedia = window.matchMedia('(max-width: 900px)');
  const menuItem = nav.querySelector('.menu');
  const menuLink = menuItem ? menuItem.querySelector('a') : null;

  const closeNav = () => {
    header.classList.remove('menu-open');
    toggle.setAttribute('aria-expanded', 'false');
    if (menuItem) {
      menuItem.classList.remove('is-open');
    }
  };

  const openNav = () => {
    header.classList.add('menu-open');
    header.classList.remove('header--hidden');
    toggle.setAttribute('aria-expanded', 'true');
  };

  toggle.addEventListener('click', () => {
    const isOpen = header.classList.contains('menu-open');
    if (isOpen) {
      closeNav();
    } else {
      openNav();
    }
  });

  if (menuLink && menuItem) {
    menuLink.addEventListener('click', (event) => {
      if (!mobileMedia.matches) {
        return;
      }

      event.preventDefault();
      menuItem.classList.toggle('is-open');
      openNav();
    });
  }

  nav.querySelectorAll('a').forEach((anchor) => {
    anchor.addEventListener('click', () => {
      if (!mobileMedia.matches) {
        return;
      }

      if (menuLink && anchor === menuLink) {
        return;
      }

      closeNav();
    });
  });

  document.addEventListener('click', (event) => {
    if (!mobileMedia.matches || !header.classList.contains('menu-open')) {
      return;
    }

    if (header.contains(event.target)) {
      return;
    }

    closeNav();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeNav();
    }
  });

  window.addEventListener('resize', () => {
    if (!mobileMedia.matches) {
      closeNav();
    }
  });
})();

(() => {
  const slides = Array.from(document.querySelectorAll('.top-slide'));
  if (slides.length < 2) {
    return;
  }

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let activeIndex = 0;

  const showSlide = (nextIndex) => {
    slides[activeIndex].classList.remove('is-active');
    activeIndex = nextIndex;
    slides[activeIndex].classList.add('is-active');
  };

  if (reduceMotion) {
    slides.forEach((slide, index) => {
      slide.classList.toggle('is-active', index === 0);
    });
    return;
  }

  window.setInterval(() => {
    const nextIndex = (activeIndex + 1) % slides.length;
    showSlide(nextIndex);
  }, 5000);
})();
