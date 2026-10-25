/* MIT: full-text search for the small bilingual developer documentation. */
var allowSearch = false;
var documents = [];
function normalize(value) { return String(value).normalize('NFKC').toLocaleLowerCase(); }
async function init() {
  var path = typeof importScripts === 'function'
    ? 'search_index.json' : joinUrl(base_url, 'search/search_index.json');
  var response = await fetch(path);
  if (!response.ok) throw Error('Cannot load the documentation search index');
  var data = await response.json();
  documents = data.docs.map(function (doc) {
    return Object.assign({}, doc, {haystack: normalize(doc.title + ' ' + doc.text)});
  });
  allowSearch = true;
  postMessage({config: {min_search_length: 2}});
  postMessage({allowSearch: true});
}
function search(query) {
  if (!allowSearch) return [];
  var terms = normalize(query).trim().slice(0, 256).split(/\s+/).filter(Boolean);
  if (!terms.length) return [];
  return documents.filter(function (doc) {
    return terms.every(function (term) { return doc.haystack.includes(term); });
  }).map(function (doc) {
    var position = normalize(doc.text).indexOf(terms[0]);
    var start = Math.max(0, position - 55);
    return {location: doc.location, title: doc.title,
      summary: (start ? '…' : '') + doc.text.slice(start, start + 220),
      score: terms.filter(function (term) { return normalize(doc.title).includes(term); }).length};
  }).sort(function (a, b) { return b.score - a.score; }).slice(0, 30);
}
if (typeof importScripts === 'function') {
  onmessage = function (event) {
    if (event.data.init) {
      init().catch(function (error) { console.error(error); postMessage({results: []}); });
    } else if (typeof event.data.query === 'string') {
      postMessage({results: search(event.data.query)});
    }
  };
}
