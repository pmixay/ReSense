export const NAVIGATION_SNAPSHOT_EVENT = 'resense:navigation-snapshot';

export interface NavigationSnapshot {
  nodes: HTMLElement[];
  scroll: Array<{ node: HTMLElement; top: number; left: number }>;
  chromeHeight: string;
}

export function mountNavigationSnapshot(target: HTMLElement, snapshot: NavigationSnapshot): void {
  target.replaceChildren(...snapshot.nodes);
  target.style.setProperty('--site-chrome-h', snapshot.chromeHeight);
  for (const { node, top, left } of snapshot.scroll) { node.scrollTop = top; node.scrollLeft = left; }
}

/** Copy a frozen endpoint for a sharp/blurred opacity crossfade; never re-render a GPU scene. */
export function duplicateNavigationSnapshot(snapshot: NavigationSnapshot): NavigationSnapshot {
  const [chrome, page] = snapshot.nodes;
  const copy = navigationSnapshot(chrome, page, false);
  copy.chromeHeight = snapshot.chromeHeight;
  const originals = snapshot.nodes.flatMap(node => [node, ...node.querySelectorAll<HTMLElement>('*')]);
  const copies = copy.nodes.flatMap(node => [node, ...node.querySelectorAll<HTMLElement>('*')]);
  copy.scroll = snapshot.scroll.map(({ node, top, left }) => ({ node: copies[originals.indexOf(node)], top, left }));
  return copy;
}

/** A short-lived DOM snapshot, including a freshly rendered copy of live canvas pixels. */
export function navigationSnapshot(chrome: HTMLElement, page: HTMLElement, refreshCanvas = true): NavigationSnapshot {
  const scroll: NavigationSnapshot['scroll'] = [];
  const nodes = [chrome, page].map(source => {
    const cloned = source.cloneNode(true) as HTMLElement;
    // Keep the single real <main> landmark and unique IDs in the live application.
    const target = document.createElement('div');
    for (const attribute of cloned.attributes) if (attribute.name !== 'id') target.setAttribute(attribute.name, attribute.value);
    target.append(...Array.from(cloned.childNodes));
    const originals = [source, ...source.querySelectorAll<HTMLElement>('*')];
    const copies = [target, ...target.querySelectorAll<HTMLElement>('*')];
    originals.forEach((original, i) => {
      const copy = copies[i];
      copy.removeAttribute('id');
      if (original.scrollTop || original.scrollLeft) scroll.push({ node: copy, top: original.scrollTop, left: original.scrollLeft });
      if (original instanceof HTMLCanvasElement && copy instanceof HTMLCanvasElement) {
        if (refreshCanvas) original.dispatchEvent(new Event(NAVIGATION_SNAPSHOT_EVENT));
        copy.width = original.width;
        copy.height = original.height;
        try { copy.getContext('2d')?.drawImage(original, 0, 0); } catch { /* Lost contexts already have a page-level recovery state. */ }
      } else if (original instanceof HTMLInputElement && copy instanceof HTMLInputElement) {
        copy.value = original.value;
        copy.checked = original.checked;
      } else if (original instanceof HTMLTextAreaElement && copy instanceof HTMLTextAreaElement) copy.value = original.value;
      else if (original instanceof HTMLSelectElement && copy instanceof HTMLSelectElement) copy.selectedIndex = original.selectedIndex;
    });
    return target;
  });
  return { nodes, scroll, chromeHeight: getComputedStyle(chrome.parentElement!).getPropertyValue('--site-chrome-h') };
}
