import React, { useEffect, useRef } from 'react';

export default function AudioWaveform({ isListening, isSpeaking }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationId;
    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      // Color scheme based on active state
      let strokeColor = '#334155'; // idle slate
      let glowColor = 'rgba(51, 65, 85, 0.2)';
      let amplitude = 4;
      let speed = 0.03;

      if (isSpeaking) {
        strokeColor = '#10b981'; // emerald green
        glowColor = 'rgba(16, 185, 129, 0.4)';
        amplitude = 22;
        speed = 0.08;
      } else if (isListening) {
        strokeColor = '#3b82f6'; // electric blue
        glowColor = 'rgba(59, 130, 246, 0.4)';
        amplitude = 18;
        speed = 0.06;
      }

      ctx.save();
      ctx.shadowBlur = isListening || isSpeaking ? 15 : 0;
      ctx.shadowColor = glowColor;

      // Draw 3 layered sine waves
      for (let wave = 0; wave < 3; wave++) {
        ctx.beginPath();
        ctx.lineWidth = wave === 1 ? 2.5 : 1.5;
        ctx.strokeStyle = strokeColor;
        ctx.globalAlpha = wave === 1 ? 1 : 0.4;

        for (let x = 0; x < width; x += 2) {
          const freq = 0.025 + wave * 0.01;
          const currentAmp = amplitude * (1 - Math.abs((x - width / 2) / (width / 2))); // taper at edges
          const y = centerY + Math.sin(x * freq + phase + wave * 1.5) * currentAmp;
          if (x === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.stroke();
      }

      ctx.restore();
      phase += speed;
      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [isListening, isSpeaking]);

  return (
    <div className="w-full flex items-center justify-center">
      <canvas
        ref={canvasRef}
        width={360}
        height={80}
        className="w-full max-w-[360px] h-[80px]"
      />
    </div>
  );
}
