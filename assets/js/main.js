/**
* Template Name: iPortfolio - v3.1.0
* Template URL: https://bootstrapmade.com/iportfolio-bootstrap-portfolio-websites-template/
* Author: BootstrapMade.com
* License: https://bootstrapmade.com/license/
*/
(function() {
  "use strict";

  /**
   * Easy selector helper function
   */
  const select = (el, all = false) => {
    el = el.trim()
    if (all) {
      return [...document.querySelectorAll(el)]
    } else {
      return document.querySelector(el)
    }
  }

  /**
   * Easy event listener function
   */
  const on = (type, el, listener, all = false) => {
    let selectEl = select(el, all)
    if (selectEl) {
      if (all) {
        selectEl.forEach(e => e.addEventListener(type, listener))
      } else {
        selectEl.addEventListener(type, listener)
      }
    }
  }

  /**
   * Easy on scroll event listener 
   */
  const onscroll = (el, listener) => {
    el.addEventListener('scroll', listener)
  }

  const scriptPromises = {}
  const loadScript = (src) => {
    if (!scriptPromises[src]) {
      scriptPromises[src] = new Promise((resolve, reject) => {
        const script = document.createElement('script')
        script.src = src
        script.defer = true
        script.onload = resolve
        script.onerror = reject
        document.body.appendChild(script)
      })
    }

    return scriptPromises[src]
  }

  /**
   * Navbar links active state on scroll
   */
  let navbarlinks = select('#navbar .scrollto', true)
  const navbarlinksActive = () => {
    let position = window.scrollY + 200
    navbarlinks.forEach(navbarlink => {
      if (!navbarlink.hash) return
      let section = select(navbarlink.hash)
      if (!section) return
      if (position >= section.offsetTop && position <= (section.offsetTop + section.offsetHeight)) {
        navbarlink.classList.add('active')
      } else {
        navbarlink.classList.remove('active')
      }
    })
  }
  window.addEventListener('load', navbarlinksActive)
  onscroll(document, navbarlinksActive)

  /**
   * Scrolls to an element with header offset
   */
  const scrollto = (el) => {
    let elementPos = select(el).offsetTop
    window.scrollTo({
      top: elementPos,
      behavior: 'smooth'
    })
  }

  /**
   * Back to top button
   */
  let backtotop = select('.back-to-top')
  if (backtotop) {
    const toggleBacktotop = () => {
      if (window.scrollY > 100) {
        backtotop.classList.add('active')
      } else {
        backtotop.classList.remove('active')
      }
    }
    window.addEventListener('load', toggleBacktotop)
    onscroll(document, toggleBacktotop)
  }

  /**
   * Mobile nav toggle
   */
  on('click', '.mobile-nav-toggle', function(e) {
    select('body').classList.toggle('mobile-nav-active')
    this.classList.toggle('bi-list')
    this.classList.toggle('bi-x')
  })

  /**
   * Scrool with ofset on links with a class name .scrollto
   */
  on('click', '.scrollto', function(e) {
    if (select(this.hash)) {
      e.preventDefault()

      let body = select('body')
      if (body.classList.contains('mobile-nav-active')) {
        body.classList.remove('mobile-nav-active')
        let navbarToggle = select('.mobile-nav-toggle')
        navbarToggle.classList.toggle('bi-list')
        navbarToggle.classList.toggle('bi-x')
      }
      scrollto(this.hash)
    }
  }, true)

  /**
   * Scroll with ofset on page load with hash links in the url
   */
  window.addEventListener('load', () => {
    if (window.location.hash) {
      if (select(window.location.hash)) {
        scrollto(window.location.hash)
      }
    }
  });

  /**
   * Hero type effect
   */
  const typed = select('.typed')
    if (typed) {
      let typed_strings = typed.getAttribute('data-typed-items')
      typed_strings = typed_strings.split(',')
      new Typed('.typed', {
        strings: typed_strings,
        contentType: 'null',
        loop: true,
        typeSpeed: 100,
        backSpeed: 50,
        backDelay: 2000
      });
  }

  /**
   * Porfolio isotope and filter
   */
  let portfolioIsotope = null
  let portfolioLoadPromise = null

  const initPortfolio = () => {
    if (portfolioIsotope) return Promise.resolve(portfolioIsotope)
    if (portfolioLoadPromise) return portfolioLoadPromise

    const portfolioContainer = select('.portfolio-container')
    if (!portfolioContainer) return Promise.resolve(null)

    const setupPortfolio = () => {
      if (portfolioIsotope) return portfolioIsotope

      portfolioIsotope = new Isotope(portfolioContainer, {
        itemSelector: '.portfolio-item'
      })

      return portfolioIsotope
    }

    portfolioLoadPromise = typeof Isotope !== 'undefined'
      ? Promise.resolve(setupPortfolio())
      : loadScript('assets/vendor/isotope-layout/isotope.pkgd.min.js').then(setupPortfolio)

    return portfolioLoadPromise
  }

  const portfolioFilters = select('#portfolio-flters li', true)

  if (portfolioFilters.length) {
    on('click', '#portfolio-flters li', function(e) {
      e.preventDefault()

      portfolioFilters.forEach(function(el) {
        el.classList.remove('filter-active')
      })
      this.classList.add('filter-active')

      initPortfolio().then((isotope) => {
        if (!isotope) return

        isotope.arrange({
          filter: this.getAttribute('data-filter')
        })

        isotope.on('arrangeComplete', function() {
          if (typeof AOS === 'undefined') return
          AOS.refresh()
        })
      })
    }, true)
  }

  const observePortfolio = () => {
    const projects = select('#projects')
    if (!projects) return

    if ('IntersectionObserver' in window) {
      const portfolioObserver = new IntersectionObserver((entries, observer) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          initPortfolio()
          observer.disconnect()
        }
      }, {
        rootMargin: '800px 0px'
      })

      portfolioObserver.observe(projects)
    } else {
      window.addEventListener('load', initPortfolio)
    }
  }

  observePortfolio()

  /**
   * Short CV expansion
   */
  let resumeColumns = select('.resume .resume-column', true)

  const updateResumeColumns = () => {
    resumeColumns.forEach((column) => {
      const button = column.querySelector('.resume-toggle')
      const extra = column.querySelector('.resume-extra')

      if (!button || !extra) return

      const expanded = button.getAttribute('aria-expanded') === 'true'
      column.classList.toggle('is-expanded', expanded)
      extra.setAttribute('aria-hidden', expanded ? 'false' : 'true')
      extra.style.maxHeight = expanded ? `${extra.scrollHeight}px` : '0px'
    })
  }

  if (resumeColumns.length) {
    resumeColumns.forEach((column) => {
      const button = column.querySelector('.resume-toggle')
      if (!button) return

      button.addEventListener('click', () => {
        const isExpanded = button.getAttribute('aria-expanded') === 'true'
        const nextExpanded = !isExpanded
        const label = button.querySelector('.resume-toggle-label')

        button.setAttribute('aria-expanded', nextExpanded ? 'true' : 'false')

        if (label) {
          label.textContent = nextExpanded
            ? button.dataset.expandedLabel
            : button.dataset.collapsedLabel
        }

        updateResumeColumns()
      })
    })

    updateResumeColumns()
    window.addEventListener('resize', updateResumeColumns)
  }

  /**
   * Animation on scroll
   */
  window.addEventListener('load', () => {
    AOS.init({
      duration: 1000,
      easing: 'ease-in-out',
      once: true,
      mirror: false
    })
  });
})()
