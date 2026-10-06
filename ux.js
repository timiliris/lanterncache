/* Presentation helpers. Network requests and download decisions stay in app.js. */
(() => {
  'use strict';
  const locks = new Map();
  let lastControl = null, toastTimer, announcementTimer, connectionState;
  const mutationControls = '#feature-start, [data-start], [data-game], #schedule-toggle, #stop, #check-steam';
  const byId = id => document.getElementById(id);
  function liveRegion() {
    let region = byId('ux-announcement');
    if (!region) {
      region = document.createElement('div');
      region.id = 'ux-announcement';
      region.className = 'visually-hidden';
      region.setAttribute('role', 'status');
      region.setAttribute('aria-live', 'polite');
      region.setAttribute('aria-atomic', 'true');
      document.body.append(region);
    }
    return region;
  }
  function announce(message) {
    const region = liveRegion();
    region.textContent = '';
    clearTimeout(announcementTimer);
    announcementTimer = setTimeout(() => { region.textContent = String(message || ''); }, 50);
  }
  function toast(message, options = {}) {
    const element = byId('toast');
    if (!element) { announce(message); return; }
    const error = Boolean(options.error);
    element.setAttribute('role', error ? 'alert' : 'status');
    element.setAttribute('aria-live', error ? 'assertive' : 'polite');
    element.setAttribute('aria-atomic', 'true');
    element.textContent = String(message || '');
    element.classList.toggle('error', error);
    element.classList.add('visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => element.classList.remove('visible'), options.duration ?? (error ? 8000 : 5000));
  }
  function beginAction(element = lastControl) {
    const token = Symbol('action');
    const controls = [...document.querySelectorAll(mutationControls)];
    const saved = controls.map(control => [control, control.disabled]);
    for (const control of controls) control.disabled = true;
    const target = element instanceof HTMLElement ? element : null;
    if (target) { target.classList.add('is-loading'); target.setAttribute('aria-busy', 'true'); }
    document.body.classList.add('action-pending');
    locks.set(token, { saved, target });
    return token;
  }
  function endAction(token) {
    const lock = locks.get(token);
    if (!lock) return;
    locks.delete(token);
    for (const [control, disabled] of lock.saved) if (control.isConnected) control.disabled = disabled;
    if (lock.target) { lock.target.classList.remove('is-loading'); lock.target.removeAttribute('aria-busy'); }
    if (!locks.size) document.body.classList.remove('action-pending');
  }
  function setConnection(online, message = '') {
    let banner = byId('connection-banner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'connection-banner';
      banner.className = 'connection-banner';
      banner.setAttribute('role', 'status');
      banner.setAttribute('aria-live', 'polite');
      banner.hidden = true;
      const heading = document.querySelector('.page-heading');
      if (heading) heading.after(banner);
    }
    banner.textContent = String(message || '');
    banner.hidden = Boolean(online) || !message;
    document.body.classList.toggle('cache-offline', !online);
    document.body.classList.toggle('state-ready', true);
    if (connectionState !== online && message && online) announce(message);
    connectionState = online;
  }
  function setActive(active) {
    document.body.classList.toggle('download-active', Boolean(active));
    // The server does not expose a total byte target, so this is activity, not a percentage.
    let indicator = byId('download-activity');
    if (!indicator) {
      indicator = document.createElement('span');
      indicator.id = 'download-activity';
      indicator.className = 'download-activity';
      indicator.setAttribute('aria-hidden', 'true');
      byId('engine-detail')?.after(indicator);
    }
    indicator.hidden = !active;
  }
  document.addEventListener('click', event => {
    const control = event.target instanceof Element ? event.target.closest('button, input') : null;
    if (control) lastControl = control;
  }, true);
  document.addEventListener('change', event => {
    if (event.target instanceof HTMLInputElement) lastControl = event.target;
  }, true);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') byId('toast')?.classList.remove('visible');
  });
  window.CacheflowUX = { toast, announce, beginAction, endAction, setConnection, setActive };
  function initialize() {
    liveRegion();
    const observed = ['overview-area', 'games-area', 'activity-area', 'planning-area', 'logs-area'];
    const observer = new MutationObserver(records => {
      for (const { target, oldValue } of records) {
        if ((oldValue || '').split(/\s+/).includes('hidden') && !target.classList.contains('hidden')) {
          target.classList.remove('view-enter');
          void target.offsetWidth;
          target.classList.add('view-enter');
        }
      }
    });
    observed.forEach(id => { const element = byId(id); if (element) observer.observe(element, { attributes: true, attributeFilter: ['class'], attributeOldValue: true }); });
    requestAnimationFrame(() => document.body.classList.add('ux-ready'));
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once: true });
  else initialize();
})();
