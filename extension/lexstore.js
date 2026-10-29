// SPDX-License-Identifier: Apache-2.0
// The imported dictionary lives in IndexedDB, one record per headword, so the background page
// never has to re-parse it when it wakes: it reads only the words a page needs.
// Keys starting with a space ("<space>전기") list the phrase headwords that begin with that word.
const NAME = 'gukhan-lexicon', STORE = 'words';

function open() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
const done = tx => new Promise((resolve, reject) => { tx.oncomplete = resolve; tx.onerror = tx.onabort = () => reject(tx.error); });

// Replace the stored dictionary with the entries of a parsed index (Map word -> entries).
export async function saveIndex(index) {
  const db = await open();
  try {
    let tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).clear(); await done(tx);
    const phrases = new Map(), keys = [...index.keys()];
    for (let i = 0; i < keys.length; i += 20000) {
      tx = db.transaction(STORE, 'readwrite');
      const store = tx.objectStore(STORE);
      for (const key of keys.slice(i, i + 20000)) {
        store.put(index.get(key), key);
        if (key.includes(' ')) {
          const first = ' ' + key.split(' ', 1)[0];
          phrases.set(first, [...(phrases.get(first) || []), key]);
        }
      }
      await done(tx);
    }
    tx = db.transaction(STORE, 'readwrite');
    for (const [first, list] of phrases) tx.objectStore(STORE).put(list, first);
    await done(tx);
  } finally { db.close(); }
}

// Read the records for `keys` into a Map; absent keys are omitted.
export async function readKeys(keys) {
  const db = await open();
  try {
    const tx = db.transaction(STORE, 'readonly'), store = tx.objectStore(STORE), found = new Map();
    await Promise.all([...keys].map(key => new Promise((resolve, reject) => {
      const request = store.get(key);
      request.onsuccess = () => { if (request.result !== undefined) found.set(key, request.result); resolve(); };
      request.onerror = () => reject(request.error);
    })));
    return found;
  } finally { db.close(); }
}
