// A small 3D view of one stored cloud of a run (RunDetail 3D card, Overview player card, Live).
// Placeholder with the final props: the Player agent replaces the body with the three.js scene.
export interface CloudPreviewProps {
  runId: string;
  /** processed-order position of the frame; the nearest stored cloud at or before it is shown */
  pos?: number;
  /** CSS height; the width follows the container */
  height?: number | string;
  /** allow orbiting with the mouse */
  interactive?: boolean;
  className?: string;
}

export default function CloudPreview({ height = 240, className }: CloudPreviewProps) {
  return <div className={className} style={{ height, borderRadius: 28, background: '#05070d' }} aria-hidden />;
}
