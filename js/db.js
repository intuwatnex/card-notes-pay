/* IndexedDB wrapper — on-device free storage */
const DB = (() => {
  const NAME = 'cardNotesPay';
  const VERSION = 2;
  let _db = null;

  function open() {
    return new Promise((resolve, reject) => {
      if (_db) return resolve(_db);
      const req = indexedDB.open(NAME, VERSION);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains('cards'))
          db.createObjectStore('cards', { keyPath: 'id', autoIncrement: true });
        if (!db.objectStoreNames.contains('spending')) {
          const s = db.createObjectStore('spending', { keyPath: 'id', autoIncrement: true });
          s.createIndex('byCardMonth', ['cardId', 'month']);
          s.createIndex('byMonth', 'month');
        }
        if (!db.objectStoreNames.contains('income'))
          db.createObjectStore('income', { keyPath: 'month' });
        if (!db.objectStoreNames.contains('transactions')) {
          const tx = db.createObjectStore('transactions', { keyPath: 'id', autoIncrement: true });
          tx.createIndex('byCardMonth', ['cardId', 'month']);
          tx.createIndex('byCard', 'cardId');
        }
        if (!db.objectStoreNames.contains('installments'))
          db.createObjectStore('installments', { keyPath: 'id', autoIncrement: true });
        if (!db.objectStoreNames.contains('meta'))
          db.createObjectStore('meta', { keyPath: 'key' });
      };
      req.onsuccess = () => { _db = req.result; resolve(_db); };
      req.onerror = () => reject(req.error);
    });
  }

  function tx(store, mode = 'readonly') {
    return open().then(db => db.transaction(store, mode).objectStore(store));
  }
  const done = (req) => new Promise((res, rej) => { req.onsuccess = () => res(req.result); req.onerror = () => rej(req.error); });

  async function getAll(store) { return done((await tx(store)).getAll()); }
  async function get(store, key) { return done((await tx(store)).get(key)); }
  async function put(store, val) { return done((await tx(store, 'readwrite')).put(val)); }
  async function add(store, val) { return done((await tx(store, 'readwrite')).add(val)); }
  async function del(store, key) { return done((await tx(store, 'readwrite')).delete(key)); }
  async function clear(store) { return done((await tx(store, 'readwrite')).clear()); }

  // ---- High level ----
  const cards = {
    all: () => getAll('cards'),
    get: (id) => get('cards', id),
    save: (c) => c.id ? put('cards', c) : add('cards', c),
    remove: (id) => del('cards', id),
  };
  const spending = {
    all: () => getAll('spending'),
    save: (s) => s.id ? put('spending', s) : add('spending', s),
    remove: (id) => del('spending', id),
    forMonth: async (month) => (await getAll('spending')).filter(s => s.month === month),
  };
  const income = {
    all: () => getAll('income'),
    get: (month) => get('income', month),
    save: (month, amount) => put('income', { month, amount }),
  };
  const installments = {
    all: () => getAll('installments'),
    save: (i) => i.id ? put('installments', i) : add('installments', i),
    remove: (id) => del('installments', id),
  };
  const transactions = {
    all: () => getAll('transactions'),
    forCard: async (cardId) => (await getAll('transactions')).filter(t => t.cardId === cardId),
  };
  const meta = {
    get: (k) => get('meta', k),
    set: (k, v) => put('meta', { key: k, value: v }),
  };

  async function exportAll() {
    return {
      _app: 'CardNotesPay', _version: VERSION, _exportedAt: new Date().toISOString(),
      cards: await getAll('cards'),
      spending: await getAll('spending'),
      transactions: await getAll('transactions'),
      income: await getAll('income'),
      installments: await getAll('installments'),
      meta: await getAll('meta'),
    };
  }

  const STORES = ['cards', 'spending', 'transactions', 'income', 'installments', 'meta'];
  async function importAll(data) {
    for (const store of STORES) {
      await clear(store);
      for (const row of (data[store] || [])) await put(store, row);
    }
  }

  async function wipe() {
    for (const store of STORES) await clear(store);
  }

  return { open, cards, spending, transactions, income, installments, meta, exportAll, importAll, wipe, getAll, clear };
})();
