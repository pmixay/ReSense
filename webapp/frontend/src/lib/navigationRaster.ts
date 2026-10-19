let embeddedStyles: Promise<string> | undefined;

/** Embed the existing self-hosted styles/font once; SVG foreignObject captures the real UI. */
function snapshotStyles(): Promise<string> {
  embeddedStyles ??= (async () => {
    const css = Array.from(document.styleSheets).flatMap(sheet => {
      try { return Array.from(sheet.cssRules, rule => rule.cssText).filter(rule => rule.startsWith('@font-face')); } catch { return []; }
    }).join('\n');
    const fonts = new Map<string, string>();
    for (const match of css.matchAll(/url\(["']?([^\s)"']+)["']?\)/g)) {
      const path = match[1];
      if (!/\.woff2?(?:\?|$)/.test(path) || fonts.has(path)) continue;
      const response = await fetch(new URL(path, document.baseURI));
      if (!response.ok) throw new Error('Navigation font could not be embedded');
      const bytes = new Uint8Array(await response.arrayBuffer());
      let binary = '';
      for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
      fonts.set(path, `data:font/woff2;base64,${btoa(binary)}`);
    }
    return css.replace(/url\(["']?([^\s)"']+)["']?\)/g, (original, path: string) => fonts.has(path) ? `url("${fonts.get(path)}")` : original);
  })().catch(error => {
    embeddedStyles = undefined;
    throw error;
  });
  return embeddedStyles;
}

/** Bake motion blur once into a bounded bitmap; travel never re-filters a moving DOM tree. */
export async function rasterizeNavigationBlur(source: HTMLElement, width: number, height: number): Promise<HTMLCanvasElement> {
  // Lazy page CSS may arrive between journeys, so include current rules as well as embedded fonts.
  const styles = await snapshotStyles();
  const currentStyles = Array.from(document.styleSheets).flatMap(sheet => {
    try { return Array.from(sheet.cssRules, rule => rule.cssText).filter(rule => !rule.startsWith('@font-face')); } catch { return []; }
  }).join('\n');
  const clone = source.cloneNode(true) as HTMLElement;
  clone.className = source.className.split(' ').filter(name => !name.includes('frozenBlur')).join(' ');
  const computed = getComputedStyle(source);
  clone.style.cssText = `width:${width}px;height:${height}px;position:relative;inset:auto;filter:none;visibility:visible;font:${computed.font};color:${computed.color};background:${getComputedStyle(document.body).backgroundColor};font-variant-numeric:lining-nums tabular-nums;`;
  const originals = source.querySelectorAll('canvas');
  Array.from(clone.querySelectorAll('canvas')).forEach((canvas, i) => {
    const image = document.createElement('img');
    image.src = originals[i].toDataURL();
    image.width = canvas.width;
    image.height = canvas.height;
    image.setAttribute('style', canvas.getAttribute('style') ?? '');
    image.className = canvas.className;
    canvas.replaceWith(image);
  });
  // DOM scroll offsets are not serialized into SVG images; preserve the visible crop explicitly.
  const originalNodes = [source, ...source.querySelectorAll<HTMLElement>('*')];
  const clonedNodes = [clone, ...clone.querySelectorAll<HTMLElement>('*')];
  originalNodes.forEach((node, i) => {
    if (!node.scrollTop && !node.scrollLeft) return;
    const wrapper = document.createElement('div');
    wrapper.style.cssText = `transform:translate(${-node.scrollLeft}px,${-node.scrollTop}px);width:${node.scrollWidth}px;min-height:${node.scrollHeight}px;`;
    wrapper.append(...Array.from(clonedNodes[i].childNodes));
    clonedNodes[i].append(wrapper);
    clonedNodes[i].style.overflow = 'hidden';
  });
  const style = document.createElement('style');
  style.textContent = `${styles}\n${currentStyles}\n*{animation:none!important;transition:none!important;caret-color:transparent!important}`;
  clone.prepend(style);
  const ratio = Math.min(1, 640 / width, 400 / height);
  const w = Math.max(1, Math.round(width * ratio));
  const h = Math.max(1, Math.round(height * ratio));
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${width} ${height}"><foreignObject width="100%" height="100%">${new XMLSerializer().serializeToString(clone)}</foreignObject></svg>`;
  const image = new Image();
  image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  await image.decode();
  const padding = Math.ceil(40 * ratio);
  const padded = document.createElement('canvas');
  padded.width = w + padding * 2;
  padded.height = h + padding * 2;
  const context = padded.getContext('2d')!;
  context.drawImage(image, padding, padding, w, h);
  // Clamp the edges so neighboring pages never reveal transparent blur seams.
  context.drawImage(padded, padding, padding, 1, h, 0, padding, padding, h);
  context.drawImage(padded, padding + w - 1, padding, 1, h, padding + w, padding, padding, h);
  context.drawImage(padded, 0, padding, padded.width, 1, 0, 0, padded.width, padding);
  context.drawImage(padded, 0, padding + h - 1, padded.width, 1, 0, padding + h, padded.width, padding);
  const result = document.createElement('canvas');
  result.width = w;
  result.height = h;
  const resultContext = result.getContext('2d')!;
  resultContext.filter = `blur(${32 * ratio}px)`;
  resultContext.drawImage(padded, -padding, -padding);
  padded.width = padded.height = 0;
  result.style.cssText = 'width:100%;height:100%;display:block';
  result.dataset.motionRaster = 'true';
  return result;
}
