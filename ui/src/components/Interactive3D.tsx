"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

export function Interactive3D() {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mountRef.current) return;

    const container = mountRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // --- Renderer ---
    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    container.appendChild(renderer.domElement);

    // --- Scene & Camera ---
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
    camera.position.set(0, 0, 8);

    // --- Colors ---
    const cyan = 0x06b6d4;
    const violet = 0x8b5cf6;
    const orange = 0xf97316;

    // ============================
    // Central Geometry - Torus Knot
    // ============================
    const knotGeo = new THREE.TorusKnotGeometry(1.6, 0.5, 200, 32, 2, 3);
    const knotMat = new THREE.MeshStandardMaterial({
      color: 0x111111,
      metalness: 0.95,
      roughness: 0.15,
      envMapIntensity: 1.0,
    });
    const knot = new THREE.Mesh(knotGeo, knotMat);
    scene.add(knot);

    // Wireframe overlay
    const wireGeo = new THREE.TorusKnotGeometry(1.62, 0.52, 200, 32, 2, 3);
    const wireMat = new THREE.MeshBasicMaterial({
      color: cyan,
      wireframe: true,
      transparent: true,
      opacity: 0.06,
    });
    const wireMesh = new THREE.Mesh(wireGeo, wireMat);
    scene.add(wireMesh);

    // ============================
    // Orbiting Rings
    // ============================
    const rings: THREE.Mesh[] = [];
    const ringData = [
      { radius: 3.0, tube: 0.008, color: cyan, opacity: 0.3, rotX: Math.PI / 2.5, rotZ: 0 },
      { radius: 3.5, tube: 0.006, color: violet, opacity: 0.2, rotX: -Math.PI / 3.5, rotZ: Math.PI / 6 },
      { radius: 4.0, tube: 0.005, color: orange, opacity: 0.15, rotX: Math.PI / 1.8, rotZ: -Math.PI / 4 },
      { radius: 4.5, tube: 0.004, color: cyan, opacity: 0.1, rotX: Math.PI / 4, rotZ: Math.PI / 3 },
    ];

    ringData.forEach((r) => {
      const geo = new THREE.TorusGeometry(r.radius, r.tube, 64, 200);
      const mat = new THREE.MeshBasicMaterial({
        color: r.color,
        transparent: true,
        opacity: r.opacity,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.rotation.x = r.rotX;
      mesh.rotation.z = r.rotZ;
      scene.add(mesh);
      rings.push(mesh);
    });

    // ============================
    // Floating Nodes (small spheres on orbits)
    // ============================
    const nodes: { mesh: THREE.Mesh; angle: number; radius: number; speed: number; plane: number }[] = [];
    const nodeColors = [cyan, violet, orange, 0xffffff];

    for (let i = 0; i < 12; i++) {
      const geo = new THREE.SphereGeometry(0.04, 16, 16);
      const mat = new THREE.MeshBasicMaterial({
        color: nodeColors[i % 4],
        transparent: true,
        opacity: 0.8,
      });
      const mesh = new THREE.Mesh(geo, mat);
      scene.add(mesh);

      // Glow sprite for each node
      const spriteMat = new THREE.SpriteMaterial({
        color: nodeColors[i % 4],
        transparent: true,
        opacity: 0.3,
        blending: THREE.AdditiveBlending,
      });
      const sprite = new THREE.Sprite(spriteMat);
      sprite.scale.set(0.3, 0.3, 1);
      mesh.add(sprite);

      nodes.push({
        mesh,
        angle: (Math.PI * 2 * i) / 12 + Math.random() * 0.5,
        radius: 2.8 + Math.random() * 2,
        speed: 0.15 + Math.random() * 0.25,
        plane: Math.random() * Math.PI,
      });
    }

    // ============================
    // Particle Field
    // ============================
    const particleCount = 1200;
    const pGeo = new THREE.BufferGeometry();
    const pPos = new Float32Array(particleCount * 3);
    const pColors = new Float32Array(particleCount * 3);
    const pSizes = new Float32Array(particleCount);
    const colorOptions = [
      new THREE.Color(cyan),
      new THREE.Color(violet),
      new THREE.Color(orange),
      new THREE.Color(0xffffff),
    ];

    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3;
      // Distribute in a sphere shell
      const r = 4 + Math.random() * 14;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      pPos[i3] = r * Math.sin(phi) * Math.cos(theta);
      pPos[i3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pPos[i3 + 2] = r * Math.cos(phi);

      const c = colorOptions[Math.floor(Math.random() * 4)];
      pColors[i3] = c.r;
      pColors[i3 + 1] = c.g;
      pColors[i3 + 2] = c.b;

      pSizes[i] = 0.5 + Math.random() * 1.5;
    }

    pGeo.setAttribute("position", new THREE.BufferAttribute(pPos, 3));
    pGeo.setAttribute("color", new THREE.BufferAttribute(pColors, 3));
    pGeo.setAttribute("size", new THREE.BufferAttribute(pSizes, 1));

    const pMat = new THREE.PointsMaterial({
      size: 0.03,
      vertexColors: true,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });
    const particles = new THREE.Points(pGeo, pMat);
    scene.add(particles);

    // ============================
    // Lights
    // ============================
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.1);
    scene.add(ambientLight);

    const pointLight1 = new THREE.PointLight(cyan, 8, 20);
    pointLight1.position.set(3, 3, 4);
    scene.add(pointLight1);

    const pointLight2 = new THREE.PointLight(violet, 6, 20);
    pointLight2.position.set(-3, -2, 3);
    scene.add(pointLight2);

    const pointLight3 = new THREE.PointLight(orange, 4, 15);
    pointLight3.position.set(0, 4, -3);
    scene.add(pointLight3);

    // ============================
    // Mouse & Scroll Interaction
    // ============================
    let mouseX = 0;
    let mouseY = 0;
    let targetRotX = 0;
    let targetRotY = 0;
    let scrollY = 0;
    let targetScrollY = 0;

    const onMouseMove = (e: MouseEvent) => {
      mouseX = (e.clientX / window.innerWidth) * 2 - 1;
      mouseY = -(e.clientY / window.innerHeight) * 2 + 1;
    };

    const onScroll = () => {
      scrollY = window.scrollY;
    };

    document.addEventListener("mousemove", onMouseMove);
    window.addEventListener("scroll", onScroll, { passive: true });

    // ============================
    // Animation
    // ============================
    const clock = new THREE.Clock();
    let animId: number;

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const t = clock.getElapsedTime();

      // Smooth mouse follow
      targetRotY += (mouseX * 0.6 - targetRotY) * 0.03;
      targetRotX += (mouseY * 0.4 - targetRotX) * 0.03;

      // Smooth scroll follow (gentle damping)
      targetScrollY += (scrollY - targetScrollY) * 0.035;
      const scrollFactor = targetScrollY * 0.00035;

      // Camera reacts gently to scroll
      camera.position.z = 8 + targetScrollY * 0.0006;
      camera.position.y = -targetScrollY * 0.0004;

      // Central knot - gentle auto-rotation + mouse + subtle scroll tilt
      knot.rotation.x = t * 0.06 + targetRotX + scrollFactor * 0.3;
      knot.rotation.y = t * 0.08 + targetRotY + scrollFactor * 0.4;
      knot.rotation.z = scrollFactor * 0.15;
      wireMesh.rotation.x = knot.rotation.x;
      wireMesh.rotation.y = knot.rotation.y;
      wireMesh.rotation.z = knot.rotation.z;

      // Pulse wireframe opacity
      wireMat.opacity = Math.min(0.09, 0.04 + 0.02 * Math.sin(t * 1.2) + scrollFactor * 0.01);

      // Rotate rings at calm speeds
      rings.forEach((ring, i) => {
        const speed = 0.02 + i * 0.01;
        ring.rotation.z += speed * 0.016 + scrollFactor * 0.001 * (i + 1);
        ring.rotation.x += speed * 0.006 * (i % 2 === 0 ? 1 : -1);
      });

      // Orbit nodes
      nodes.forEach((node) => {
        const a = node.angle + t * node.speed + scrollFactor * 0.4;
        node.mesh.position.x = Math.cos(a) * node.radius * Math.cos(node.plane);
        node.mesh.position.y = Math.sin(a) * node.radius * 0.6 + Math.sin(t * 0.3 + node.angle) * 0.4;
        node.mesh.position.z = Math.sin(a) * node.radius * Math.sin(node.plane);
      });

      // Slowly rotate particles with subtle parallax
      particles.rotation.y = t * 0.01 + targetRotY * 0.2 + scrollFactor * 0.1;
      particles.rotation.x = t * 0.006 + targetRotX * 0.15 + scrollFactor * 0.08;

      // Animate lights for subtle color shifts
      pointLight1.position.x = 3 * Math.cos(t * 0.25 + scrollFactor * 0.2);
      pointLight1.position.z = 4 * Math.sin(t * 0.25 + scrollFactor * 0.2);
      pointLight2.position.y = -2 + Math.sin(t * 0.3) * 1.5;
      pointLight3.position.x = 3 * Math.sin(t * 0.2 + scrollFactor * 0.2);

      renderer.render(scene, camera);
    };
    animate();

    // ============================
    // Resize
    // ============================
    const onResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    window.addEventListener("resize", onResize);

    // ============================
    // Cleanup
    // ============================
    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onScroll);
      document.removeEventListener("mousemove", onMouseMove);

      if (container && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }

      // Dispose all geometries and materials
      scene.traverse((obj) => {
        if (obj instanceof THREE.Mesh || obj instanceof THREE.Points) {
          obj.geometry.dispose();
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => m.dispose());
          } else {
            obj.material.dispose();
          }
        }
        if (obj instanceof THREE.Sprite) {
          obj.material.dispose();
        }
      });

      renderer.dispose();
    };
  }, []);

  return (
    <div
      ref={mountRef}
      className="absolute inset-0 -z-10 pointer-events-none"
      aria-hidden="true"
    />
  );
}
