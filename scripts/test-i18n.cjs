const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
async function scenario(browserLanguage, savedLanguage) {
  const storage = new Map(savedLanguage ? [['lanterncache.language', savedLanguage]] : []);
  const selector = {value: '', addEventListener: (_, cb) => selector.change = cb};
  const translated = {dataset: {i18n:'nav.games'}, textContent:''};
  const document = {
    documentElement: {lang:''},
    querySelector: () => selector,
    querySelectorAll: selector => selector === '[data-i18n]' ? [translated] : [],
    dispatchEvent: () => {}
  };
  const context = vm.createContext({
    window:{}, document, navigator:{language:browserLanguage},
    localStorage:{getItem:key=>storage.get(key),setItem:(key,value)=>storage.set(key,value)},
    CustomEvent: class {constructor(type) {this.type=type;}},
    fetch: async url=>({ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(root,url),'utf8'))})
  });
  vm.runInContext(fs.readFileSync(path.join(root,'i18n.js'),'utf8'),context);
  const i = context.window.CacheflowI18n;
  await i.init();
  assert.equal(i.language, savedLanguage || (browserLanguage.startsWith('fr')?'fr':'en'));
  assert.equal(document.documentElement.lang,i.language);
  assert.equal(translated.textContent,i.t('nav.games'));
  assert.ok(i.t('hero.prepare',{host:'example-server'}).includes('example-server'));
  selector.change({target:{value:i.language==='fr'?'en':'fr'}});
  assert.equal(storage.get('lanterncache.language'),i.language);
  assert.equal(translated.textContent,i.t('nav.games'));
  assert.equal(i.t('missing.key'),'missing.key');
}
(async()=>{await scenario('fr-BE');await scenario('en-GB');await scenario('fr-FR','en');console.log('Language detection, saved preference, switching and placeholders passed.');})().catch(error=>{console.error(error);process.exit(1);});
