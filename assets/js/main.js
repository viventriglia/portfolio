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
    const updateBacktotop = () => {
      const scrollableHeight = document.documentElement.scrollHeight - window.innerHeight
      const progress = scrollableHeight > 0
        ? Math.min(100, Math.max(0, (window.scrollY / scrollableHeight) * 100))
        : 0

      backtotop.style.setProperty('--scroll-progress', `${progress}%`)
      backtotop.classList.toggle('active', window.scrollY > 100)
    }
    window.addEventListener('load', updateBacktotop)
    onscroll(document, updateBacktotop)
  }

  /**
   * Sidebar navigation toggle
   */
  const navToggle = select('.mobile-nav-toggle')
  const navToggleIcon = navToggle ? navToggle.querySelector('i') : null
  const navigation = select('#header')
  const desktopNavigation = window.matchMedia('(min-width: 1200px)')

  const syncNavigationState = () => {
    if (!navToggle || !navigation) return

    const body = select('body')
    const isOpen = desktopNavigation.matches
      ? !body.classList.contains('sidebar-collapsed')
      : body.classList.contains('mobile-nav-active')

    navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false')
    navToggle.setAttribute('aria-label', isOpen ? 'Hide navigation' : 'Show navigation')
    navigation.setAttribute('aria-hidden', isOpen ? 'false' : 'true')
    navigation.inert = !isOpen

    if (navToggleIcon) {
      const showCloseIcon = isOpen
      navToggleIcon.classList.toggle('bi-list', !showCloseIcon)
      navToggleIcon.classList.toggle('bi-x', showCloseIcon)
    }
  }

  if (navToggle) {
    if (desktopNavigation.matches) {
      try {
        select('body').classList.toggle(
          'sidebar-collapsed',
          localStorage.getItem('sidebar-collapsed') === 'true'
        )
      } catch (error) {
        console.warn('Could not restore the sidebar preference:', error)
      }
    }

    navToggle.addEventListener('click', () => {
      const body = select('body')

      if (desktopNavigation.matches) {
        const collapsed = body.classList.toggle('sidebar-collapsed')
        try {
          localStorage.setItem('sidebar-collapsed', String(collapsed))
        } catch (error) {
          console.warn('Could not save the sidebar preference:', error)
        }
      } else {
        body.classList.toggle('mobile-nav-active')
      }

      syncNavigationState()
    })

    desktopNavigation.addEventListener('change', () => {
      select('body').classList.remove('mobile-nav-active')
      syncNavigationState()
    })

    syncNavigationState()
  }

  /**
   * Scrool with ofset on links with a class name .scrollto
   */
  on('click', '.scrollto', function(e) {
    if (select(this.hash)) {
      e.preventDefault()

      let body = select('body')
      if (body.classList.contains('mobile-nav-active')) {
        body.classList.remove('mobile-nav-active')
        syncNavigationState()
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
   * Skills animation
   */
  let skilsContent = select('.skills-content');
  if (skilsContent) {
    new Waypoint({
      element: skilsContent,
      offset: '80%',
      handler: function(direction) {
        let progress = select('.progress .progress-bar', true);
        progress.forEach((el) => {
          el.style.width = el.getAttribute('aria-valuenow') + '%'
        });
      }
    })
  }

  /**
   * Porfolio isotope and filter
   */
  window.addEventListener('load', () => {
    let portfolioContainer = select('.portfolio-container');
    if (portfolioContainer) {
      let portfolioIsotope = new Isotope(portfolioContainer, {
        itemSelector: '.portfolio-item'
      });

      let portfolioFilters = select('#portfolio-flters li', true);

      on('click', '#portfolio-flters li', function(e) {
        e.preventDefault();
        portfolioFilters.forEach(function(el) {
          el.classList.remove('filter-active');
        });
        this.classList.add('filter-active');

        portfolioIsotope.arrange({
          filter: this.getAttribute('data-filter')
        });
        portfolioIsotope.on('arrangeComplete', function() {
          AOS.refresh()
        });
      }, true);
    }

  });

  /**
   * Short CV expansion
   */
  let resumeColumns = select('.resume .resume-column', true)

  const updateResumeColumn = (column) => {
    const button = column.querySelector('.resume-toggle')
    const extra = column.querySelector('.resume-extra')

    if (!button || !extra) return

    const expanded = button.getAttribute('aria-expanded') === 'true'
    column.classList.toggle('is-expanded', expanded)
    extra.setAttribute('aria-hidden', expanded ? 'false' : 'true')
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

        updateResumeColumn(column)
      })

      updateResumeColumn(column)
    })
  }

  /**
   * Twice-weekly portfolio metrics
   */
  const metricsGrid = select('.metrics-grid')

  if (metricsGrid) {
    metricsGrid.setAttribute('aria-busy', 'true')
    fetch('./data/metrics.json', { cache: 'no-cache' })
      .then((response) => {
        if (!response.ok) throw new Error(`Metrics request failed (${response.status})`)
        return response.json()
      })
      .then((metrics) => {
        const numberFormatter = new Intl.NumberFormat('en-US')
        const compactFormatter = new Intl.NumberFormat('en-US', {
          notation: 'compact',
          maximumFractionDigits: 1
        })

        select('[data-metric]', true).forEach((element) => {
          const value = metrics[element.dataset.metric]
          if (Number.isFinite(value)) {
            element.textContent = element.dataset.metric === 'pypi_downloads'
              ? compactFormatter.format(value).replace('K', 'k')
              : numberFormatter.format(value)
          }
        })

        const updatedElement = select('[data-metrics-updated]')
        const updatedAt = new Date(metrics.updated_at)
        if (updatedElement && !Number.isNaN(updatedAt.getTime())) {
          updatedElement.textContent = new Intl.DateTimeFormat('en-GB', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
          }).format(updatedAt)
        }

        metricsGrid.setAttribute('aria-busy', 'false')
      })
      .catch((error) => {
        metricsGrid.setAttribute('aria-busy', 'false')
        console.warn('Could not load portfolio metrics:', error)
      })
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
