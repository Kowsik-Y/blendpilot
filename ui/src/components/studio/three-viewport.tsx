"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Layers,
  RotateCw,
  Eye,
  Box,
  Sliders,
  Sparkles,
  Maximize2,
} from "lucide-react";

interface ThreeViewportProps {
  assetSpec?: {
    asset_type?: string;
    dimensions?: { width: number; depth: number; height: number };
    budget?: { target_triangles?: number };
    modifiers?: string[];
  };
  wireframeMode?: boolean;
  onSelectPart?: (partName: string) => void;
}

export function ThreeViewport({
  assetSpec,
  wireframeMode = false,
  onSelectPart,
}: ThreeViewportProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const meshGroupRef = useRef<THREE.Group | null>(null);
  const rotatingPartsRef = useRef<THREE.Object3D[]>([]);

  const [wireframe, setWireframe] = useState(wireframeMode);
  const [autoRotate, setAutoRotate] = useState(false);
  const [renderMode, setRenderMode] = useState<"shaded" | "wireframe" | "clay">("shaded");
  const [cameraView, setCameraView] = useState<"iso" | "front" | "top">("iso");

  // Sync prop changes
  useEffect(() => {
    setWireframe(wireframeMode);
  }, [wireframeMode]);

  // Initialize Three.js WebGL Scene
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xffffff);
    sceneRef.current = scene;

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.1,
      100
    );
    camera.position.set(2.4, 2.0, 3.2);
    cameraRef.current = camera;

    // 3. Renderer with Anti-Aliasing & Tone Mapping
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    rendererRef.current = renderer;

    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    // 4. Orbit Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(0, 0.4, 0);
    controls.maxPolarAngle = Math.PI / 2 + 0.05;
    controls.minDistance = 0.5;
    controls.maxDistance = 15;
    controlsRef.current = controls;

    // 5. Studio 3-Point Lighting Matrix
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.8);
    keyLight.position.set(4, 8, 5);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    keyLight.shadow.bias = -0.0001;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x06b6d4, 1.0);
    fillLight.position.set(-5, 3, -4);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0xa855f7, 1.2);
    rimLight.position.set(0, 5, -6);
    scene.add(rimLight);

    // 6. Floor Grid & Shadow Catcher Plane
    const gridHelper = new THREE.GridHelper(10, 20, 0x0ea5e9, 0xe2e8f0);
    gridHelper.position.y = 0;
    scene.add(gridHelper);

    const floorGeom = new THREE.PlaneGeometry(20, 20);
    const floorMat = new THREE.ShadowMaterial({ opacity: 0.25 });
    const floor = new THREE.Mesh(floorGeom, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    // 7. Animation Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      controls.update();

      if (autoRotate && meshGroupRef.current) {
        meshGroupRef.current.rotation.y += 0.004;
      }

      // Rotate sub-parts like floating energy rings, propeller, or thrusters
      rotatingPartsRef.current.forEach((obj, idx) => {
        obj.rotation.z += 0.02 * (idx % 2 === 0 ? 1 : -1);
        obj.rotation.x += 0.01;
      });

      renderer.render(scene, camera);
    };
    animate();

    // 8. Resize Observer
    const resizeObserver = new ResizeObserver(() => {
      if (!container || !camera || !renderer) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w === 0 || h === 0) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    });
    resizeObserver.observe(container);

    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      renderer.dispose();
    };
  }, []);

  // Procedurally construct detailed production-grade 3D assets for ANY concept
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    if (meshGroupRef.current) {
      scene.remove(meshGroupRef.current);
      meshGroupRef.current = null;
    }
    rotatingPartsRef.current = [];

    const assetType = (assetSpec?.asset_type || "crate").toLowerCase();
    const w = Math.max(0.2, assetSpec?.dimensions?.width || 1.0);
    const d = Math.max(0.2, assetSpec?.dimensions?.depth || 0.7);
    const h = Math.max(0.2, assetSpec?.dimensions?.height || 0.6);

    const group = new THREE.Group();

    // Helper: Material Creator
    const createMat = (color: number, metalness = 0.8, roughness = 0.35, emissive = 0x000000, emissiveIntensity = 0) => {
      if (renderMode === "clay") {
        return new THREE.MeshStandardMaterial({ color: 0xe2e8f0, roughness: 0.9, metalness: 0.0, wireframe });
      }
      return new THREE.MeshStandardMaterial({
        color,
        metalness,
        roughness,
        emissive,
        emissiveIntensity,
        wireframe: wireframe || renderMode === "wireframe",
      });
    };

    // Helper: Add Edge Outline
    const addEdges = (mesh: THREE.Mesh, color = 0x38bdf8) => {
      if (renderMode === "wireframe") return;
      const edges = new THREE.EdgesGeometry(mesh.geometry, 25);
      const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color, linewidth: 1, transparent: true, opacity: 0.4 }));
      mesh.add(line);
    };

    // ─────────────────────────────────────────────────────────────
    // 1. SCI-FI CRATE / SUPPLY BOX / CHEST / CONTAINER
    // ─────────────────────────────────────────────────────────────
    if (assetType.includes("crate") || assetType.includes("box") || assetType.includes("chest") || assetType.includes("container")) {
      const bodyGeom = new THREE.BoxGeometry(w, h, d);
      const bodyMat = createMat(0x1e293b, 0.85, 0.3);
      const body = new THREE.Mesh(bodyGeom, bodyMat);
      body.position.y = h / 2;
      body.castShadow = true;
      body.receiveShadow = true;
      addEdges(body, 0x06b6d4);
      group.add(body);

      const panelMat = createMat(0x0f172a, 0.9, 0.2);
      const fbGeom = new THREE.BoxGeometry(w * 0.78, h * 0.78, d + 0.008);
      const fbPanel = new THREE.Mesh(fbGeom, panelMat);
      fbPanel.position.y = h / 2;
      group.add(fbPanel);

      const lrGeom = new THREE.BoxGeometry(w + 0.008, h * 0.78, d * 0.78);
      const lrPanel = new THREE.Mesh(lrGeom, panelMat);
      lrPanel.position.y = h / 2;
      group.add(lrPanel);

      // Emissive Seam Strip
      const seamGeom = new THREE.BoxGeometry(w * 1.01, h * 0.06, d * 1.01);
      const seamMat = createMat(0x06b6d4, 0.2, 0.2, 0x06b6d4, 2.4);
      const seam = new THREE.Mesh(seamGeom, seamMat);
      seam.position.y = h / 2;
      group.add(seam);

      // 8 Corner Reinforcements
      const bracketSize = Math.min(w, d, h) * 0.22;
      const bracketGeom = new THREE.BoxGeometry(bracketSize, bracketSize, bracketSize);
      const bracketMat = createMat(0x334155, 0.95, 0.2);

      const offsets = [
        [w / 2 - bracketSize / 2, h - bracketSize / 2, d / 2 - bracketSize / 2],
        [-w / 2 + bracketSize / 2, h - bracketSize / 2, d / 2 - bracketSize / 2],
        [w / 2 - bracketSize / 2, h - bracketSize / 2, -d / 2 + bracketSize / 2],
        [-w / 2 + bracketSize / 2, h - bracketSize / 2, -d / 2 + bracketSize / 2],
        [w / 2 - bracketSize / 2, bracketSize / 2, d / 2 - bracketSize / 2],
        [-w / 2 + bracketSize / 2, bracketSize / 2, d / 2 - bracketSize / 2],
        [w / 2 - bracketSize / 2, bracketSize / 2, -d / 2 + bracketSize / 2],
        [-w / 2 + bracketSize / 2, bracketSize / 2, -d / 2 + bracketSize / 2],
      ];

      offsets.forEach(([bx, by, bz]) => {
        const b = new THREE.Mesh(bracketGeom, bracketMat);
        b.position.set(bx, by, bz);
        b.castShadow = true;
        group.add(b);
      });
    }

    // ─────────────────────────────────────────────────────────────
    // 2. SWORD / BLADE / KATANA / WEAPON
    // ─────────────────────────────────────────────────────────────
    else if (assetType.includes("sword") || assetType.includes("blade") || assetType.includes("katana") || assetType.includes("weapon") || assetType.includes("dagger")) {
      const bladeLen = Math.max(0.8, h);
      const bladeW = Math.max(0.06, w);

      // Blade Spine (Double beveled prism)
      const bladeGeom = new THREE.BoxGeometry(bladeW, bladeLen, 0.015);
      const bladeMat = createMat(0xe2e8f0, 0.95, 0.15);
      const blade = new THREE.Mesh(bladeGeom, bladeMat);
      blade.position.y = 0.25 + bladeLen / 2;
      blade.castShadow = true;
      addEdges(blade, 0x06b6d4);
      group.add(blade);

      // Glowing Plasma Edge Channel
      const plasmaGeom = new THREE.BoxGeometry(bladeW * 0.25, bladeLen * 0.9, 0.02);
      const plasmaMat = createMat(0x06b6d4, 0.1, 0.1, 0x06b6d4, 3.0);
      const plasma = new THREE.Mesh(plasmaGeom, plasmaMat);
      plasma.position.y = 0.25 + bladeLen / 2;
      group.add(plasma);

      // Crossguard (Tsuba plate)
      const guardGeom = new THREE.BoxGeometry(bladeW * 3.0, 0.02, bladeW * 1.8);
      const guardMat = createMat(0x0f172a, 0.9, 0.2);
      const guard = new THREE.Mesh(guardGeom, guardMat);
      guard.position.y = 0.25;
      guard.castShadow = true;
      group.add(guard);

      // Handle Grip
      const gripGeom = new THREE.CylinderGeometry(0.025, 0.025, 0.22, 16);
      const gripMat = createMat(0x1e293b, 0.3, 0.7);
      const grip = new THREE.Mesh(gripGeom, gripMat);
      grip.position.y = 0.13;
      grip.castShadow = true;
      group.add(grip);

      // Pommel End Cap
      const pommelGeom = new THREE.SphereGeometry(0.035, 16, 16);
      const pommelMat = createMat(0xca8a04, 0.95, 0.15);
      const pommel = new THREE.Mesh(pommelGeom, pommelMat);
      pommel.position.y = 0.02;
      group.add(pommel);
    }

    // ─────────────────────────────────────────────────────────────
    // 3. TREE / FOLIAGE / NATURE / PLANT
    // ─────────────────────────────────────────────────────────────
    else if (assetType.includes("tree") || assetType.includes("foliage") || assetType.includes("plant") || assetType.includes("nature") || assetType.includes("wood")) {
      const trunkH = h * 0.45;
      const trunkR = Math.min(w, d) * 0.15;

      // Brown Tapered Trunk
      const trunkGeom = new THREE.CylinderGeometry(trunkR * 0.7, trunkR * 1.1, trunkH, 12);
      const barkMat = createMat(0x78350f, 0.1, 0.85);
      const trunk = new THREE.Mesh(trunkGeom, barkMat);
      trunk.position.y = trunkH / 2;
      trunk.castShadow = true;
      addEdges(trunk, 0x92400e);
      group.add(trunk);

      // 3-Tiered Faceted Foliage Canopies
      const canopyLevels = [
        { y: trunkH * 0.9, scale: Math.min(w, d) * 0.65, color: 0x15803d },
        { y: trunkH * 1.35, scale: Math.min(w, d) * 0.52, color: 0x16a34a },
        { y: trunkH * 1.75, scale: Math.min(w, d) * 0.38, color: 0x22c55e },
      ];

      canopyLevels.forEach(({ y, scale, color }) => {
        const geom = new THREE.IcosahedronGeometry(scale, 1);
        const mat = createMat(color, 0.1, 0.6);
        const foliage = new THREE.Mesh(geom, mat);
        foliage.position.y = y;
        foliage.castShadow = true;
        addEdges(foliage, 0x86efac);
        group.add(foliage);
      });
    }

    // ─────────────────────────────────────────────────────────────
    // 4. SCI-FI VEHICLE / CAR / SPACESHIP / CRAFT
    // ─────────────────────────────────────────────────────────────
    else if (assetType.includes("car") || assetType.includes("vehicle") || assetType.includes("ship") || assetType.includes("spaceship") || assetType.includes("craft")) {
      const chassisLen = Math.max(1.8, d);
      const chassisW = Math.max(0.9, w);
      const chassisH = Math.max(0.45, h * 0.5);

      // Main Chassis Body
      const chassisGeom = new THREE.BoxGeometry(chassisW, chassisH, chassisLen);
      const paintMat = createMat(0x0f172a, 0.9, 0.2);
      const chassis = new THREE.Mesh(chassisGeom, paintMat);
      chassis.position.y = 0.25 + chassisH / 2;
      chassis.castShadow = true;
      addEdges(chassis, 0x06b6d4);
      group.add(chassis);

      // Cockpit Canopy Glass
      const cockpitGeom = new THREE.BoxGeometry(chassisW * 0.7, chassisH * 0.8, chassisLen * 0.45);
      const glassMat = createMat(0x06b6d4, 0.95, 0.1, 0x06b6d4, 1.2);
      const cockpit = new THREE.Mesh(cockpitGeom, glassMat);
      cockpit.position.set(0, 0.25 + chassisH * 1.3, -chassisLen * 0.05);
      group.add(cockpit);

      // 4 High-Traction Wheels / Thrusters
      const wheelGeom = new THREE.CylinderGeometry(0.18, 0.18, 0.12, 20);
      const wheelMat = createMat(0x1e293b, 0.8, 0.4);

      const wheelOffsets = [
        [chassisW / 2 + 0.06, 0.18, chassisLen * 0.3],
        [-chassisW / 2 - 0.06, 0.18, chassisLen * 0.3],
        [chassisW / 2 + 0.06, 0.18, -chassisLen * 0.3],
        [-chassisW / 2 - 0.06, 0.18, -chassisLen * 0.3],
      ];

      wheelOffsets.forEach(([wx, wy, wz]) => {
        const wheel = new THREE.Mesh(wheelGeom, wheelMat);
        wheel.rotation.z = Math.PI / 2;
        wheel.position.set(wx, wy, wz);
        wheel.castShadow = true;
        group.add(wheel);
      });
    }

    // ─────────────────────────────────────────────────────────────
    // 5. DINING TABLE / DESK / BENCH
    // ─────────────────────────────────────────────────────────────
    else if (assetType.includes("table") || assetType.includes("desk") || assetType.includes("bench")) {
      const topThick = 0.06;
      const legW = 0.06;
      const topGeom = new THREE.BoxGeometry(w, topThick, d);
      const woodMat = createMat(0xa16207, 0.15, 0.65);
      const top = new THREE.Mesh(topGeom, woodMat);
      top.position.y = h - topThick / 2;
      top.castShadow = true;
      addEdges(top, 0xca8a04);
      group.add(top);

      const legH = h - topThick;
      const legGeom = new THREE.BoxGeometry(legW, legH, legW);
      const legMat = createMat(0x1e293b, 0.9, 0.25);

      [
        [w / 2 - legW, d / 2 - legW],
        [-w / 2 + legW, d / 2 - legW],
        [w / 2 - legW, -d / 2 + legW],
        [-w / 2 + legW, -d / 2 + legW],
      ].forEach(([lx, lz]) => {
        const leg = new THREE.Mesh(legGeom, legMat);
        leg.position.set(lx, legH / 2, lz);
        leg.castShadow = true;
        group.add(leg);
      });

      const railGeom = new THREE.BoxGeometry(w * 0.75, topThick * 0.6, legW * 0.8);
      const rail = new THREE.Mesh(railGeom, legMat);
      rail.position.set(0, h - topThick * 1.5, 0);
      group.add(rail);
    }

    // ─────────────────────────────────────────────────────────────
    // 6. BARREL / DRUM / TANK
    // ─────────────────────────────────────────────────────────────
    else if (assetType.includes("barrel") || assetType.includes("drum") || assetType.includes("tank")) {
      const radius = Math.min(w, d) / 2;
      const staveGeom = new THREE.CylinderGeometry(radius * 0.88, radius * 0.88, h, 28);
      const woodMat = createMat(0x854d0e, 0.1, 0.7);
      const barrelBody = new THREE.Mesh(staveGeom, woodMat);
      barrelBody.position.y = h / 2;
      barrelBody.castShadow = true;
      addEdges(barrelBody, 0xca8a04);
      group.add(barrelBody);

      const bulgeGeom = new THREE.CylinderGeometry(radius * 1.02, radius * 1.02, h * 0.45, 28);
      const bulge = new THREE.Mesh(bulgeGeom, woodMat);
      bulge.position.y = h / 2;
      group.add(bulge);

      const hoopMat = createMat(0x334155, 0.9, 0.25);
      const hoopGeom = new THREE.TorusGeometry(radius * 0.96, radius * 0.025, 12, 32);

      [0.15, 0.38, 0.62, 0.85].forEach((ratio) => {
        const hoop = new THREE.Mesh(hoopGeom, hoopMat);
        hoop.rotation.x = Math.PI / 2;
        hoop.position.y = h * ratio;
        hoop.castShadow = true;
        group.add(hoop);
      });
    }

    // ─────────────────────────────────────────────────────────────
    // 7. SCI-FI ENERGY PYLON / TOWER / BEACON
    // ─────────────────────────────────────────────────────────────
    else if (assetType.includes("pylon") || assetType.includes("tower") || assetType.includes("beacon") || assetType.includes("generator")) {
      const base1Geom = new THREE.BoxGeometry(w, h * 0.08, d);
      const darkMetalMat = createMat(0x0f172a, 0.95, 0.2);
      const base1 = new THREE.Mesh(base1Geom, darkMetalMat);
      base1.position.y = h * 0.04;
      base1.castShadow = true;
      group.add(base1);

      const prongW = w * 0.12;
      const prongH = h * 0.75;
      const prongGeom = new THREE.BoxGeometry(prongW, prongH, prongW);
      const prongMat = createMat(0x1e293b, 0.9, 0.25);

      const prongOffsets = [
        [w * 0.3, d * 0.3],
        [-w * 0.3, d * 0.3],
        [w * 0.3, -d * 0.3],
        [-w * 0.3, -d * 0.3],
      ];

      prongOffsets.forEach(([px, pz]) => {
        const prong = new THREE.Mesh(prongGeom, prongMat);
        prong.position.set(px, h * 0.16 + prongH / 2, pz);
        prong.castShadow = true;
        addEdges(prong, 0x06b6d4);
        group.add(prong);

        const stripGeom = new THREE.BoxGeometry(prongW * 1.05, prongH * 0.6, prongW * 0.2);
        const glowMat = createMat(0x06b6d4, 0.1, 0.2, 0x06b6d4, 2.5);
        const strip = new THREE.Mesh(stripGeom, glowMat);
        strip.position.set(px, h * 0.16 + prongH / 2, pz);
        group.add(strip);
      });

      const coreGeom = new THREE.OctahedronGeometry(w * 0.22, 2);
      const coreMat = createMat(0x06b6d4, 0.1, 0.1, 0x06b6d4, 3.0);
      const core = new THREE.Mesh(coreGeom, coreMat);
      core.position.y = h * 0.55;
      group.add(core);

      const ringGeom = new THREE.TorusGeometry(w * 0.35, 0.018, 16, 32);
      const ringMat = createMat(0xa855f7, 0.2, 0.2, 0xa855f7, 2.0);
      const ring = new THREE.Mesh(ringGeom, ringMat);
      ring.position.y = h * 0.55;
      ring.rotation.x = Math.PI / 3;
      group.add(ring);
      rotatingPartsRef.current.push(ring);
    }

    // ─────────────────────────────────────────────────────────────
    // 8. CHAIR / STOOL / SEAT
    // ─────────────────────────────────────────────────────────────
    else if (assetType.includes("chair") || assetType.includes("stool") || assetType.includes("seat")) {
      const seatH = h * 0.45;
      const seatGeom = new THREE.BoxGeometry(w, 0.05, d);
      const seatMat = createMat(0x1e293b, 0.6, 0.4);
      const seat = new THREE.Mesh(seatGeom, seatMat);
      seat.position.y = seatH;
      seat.castShadow = true;
      addEdges(seat, 0x06b6d4);
      group.add(seat);

      const backH = h - seatH;
      const backGeom = new THREE.BoxGeometry(w, backH, 0.04);
      const back = new THREE.Mesh(backGeom, seatMat);
      back.position.set(0, seatH + backH / 2, -d / 2 + 0.02);
      back.castShadow = true;
      addEdges(back, 0x06b6d4);
      group.add(back);

      const legGeom = new THREE.BoxGeometry(0.04, seatH, 0.04);
      const legMat = createMat(0xd97706, 0.95, 0.2);

      [
        [w / 2 - 0.04, d / 2 - 0.04],
        [-w / 2 + 0.04, d / 2 - 0.04],
        [w / 2 - 0.04, -d / 2 + 0.04],
        [-w / 2 + 0.04, -d / 2 + 0.04],
      ].forEach(([lx, lz]) => {
        const leg = new THREE.Mesh(legGeom, legMat);
        leg.position.set(lx, seatH / 2, lz);
        leg.castShadow = true;
        group.add(leg);
      });
    }

    // ─────────────────────────────────────────────────────────────
    // 9. DYNAMIC COMPOUND PROCEDURAL MODEL (For ANY other prompt)
    // ─────────────────────────────────────────────────────────────
    else {
      // Main Center Core Mesh
      const mainGeom = new THREE.BoxGeometry(w, h * 0.7, d);
      const mainMat = createMat(0x1e293b, 0.85, 0.35);
      const mainMesh = new THREE.Mesh(mainGeom, mainMat);
      mainMesh.position.y = (h * 0.7) / 2 + h * 0.15;
      mainMesh.castShadow = true;
      mainMesh.receiveShadow = true;
      addEdges(mainMesh, 0x06b6d4);
      group.add(mainMesh);

      // Top Crown / Accent
      const topGeom = new THREE.CylinderGeometry(Math.min(w, d) * 0.35, Math.min(w, d) * 0.45, h * 0.2, 16);
      const topMat = createMat(0x0f172a, 0.95, 0.2);
      const topMesh = new THREE.Mesh(topGeom, topMat);
      topMesh.position.y = h * 0.9;
      topMesh.castShadow = true;
      group.add(topMesh);

      // Base Support Slabs
      const baseGeom = new THREE.BoxGeometry(w * 1.15, h * 0.12, d * 1.15);
      const baseMat = createMat(0x0f172a, 0.9, 0.25);
      const baseMesh = new THREE.Mesh(baseGeom, baseMat);
      baseMesh.position.y = h * 0.06;
      baseMesh.castShadow = true;
      group.add(baseMesh);

      // Glowing Center Accent Strip
      const stripGeom = new THREE.BoxGeometry(w * 1.02, h * 0.08, d * 1.02);
      const stripMat = createMat(0x06b6d4, 0.2, 0.2, 0x06b6d4, 2.2);
      const strip = new THREE.Mesh(stripGeom, stripMat);
      strip.position.y = (h * 0.7) / 2 + h * 0.15;
      group.add(strip);
    }

    scene.add(group);
    meshGroupRef.current = group;
  }, [assetSpec, wireframe, renderMode]);

  const handleSetView = (view: "iso" | "front" | "top") => {
    setCameraView(view);
    if (!cameraRef.current || !controlsRef.current) return;

    if (view === "iso") {
      cameraRef.current.position.set(2.4, 2.0, 3.2);
      controlsRef.current.target.set(0, 0.4, 0);
    } else if (view === "front") {
      cameraRef.current.position.set(0, 0.6, 4.0);
      controlsRef.current.target.set(0, 0.5, 0);
    } else if (view === "top") {
      cameraRef.current.position.set(0, 4.5, 0.01);
      controlsRef.current.target.set(0, 0, 0);
    }
    controlsRef.current.update();
  };

  return (
    <div className="relative w-full h-full min-h-[480px] rounded-2xl overflow-hidden border border-border bg-gradient-to-b from-card/90 via-card/70 to-background backdrop-blur-xl shadow-2xl flex flex-col">
      {/* Top Floating Control Bar */}
      <div className="absolute top-4 left-4 right-4 z-10 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-2 pointer-events-auto">
          <Badge variant="outline" className="bg-background/85 backdrop-blur-md border-cyan-500/40 text-cyan-300 text-xs px-2.5 py-1 font-semibold">
            <Box className="w-3.5 h-3.5 mr-1 text-cyan-400" />
            {assetSpec?.asset_type ? assetSpec.asset_type.toUpperCase() : "READY"}
          </Badge>
          {assetSpec?.dimensions && (
            <Badge variant="secondary" className="bg-background/75 backdrop-blur-md text-xs text-muted-foreground font-mono">
              {assetSpec.dimensions.width.toFixed(2)}m × {assetSpec.dimensions.depth.toFixed(2)}m × {assetSpec.dimensions.height.toFixed(2)}m
            </Badge>
          )}
        </div>

        {/* Viewport Control Badges & Tools */}
        <div className="flex items-center gap-1 pointer-events-auto bg-background/85 backdrop-blur-md p-1 rounded-xl border border-border shadow-lg">
          {/* Camera View Switcher */}
          <div className="flex bg-muted/40 p-0.5 rounded-lg mr-1">
            <button
              onClick={() => handleSetView("iso")}
              className={`text-[11px] px-2 py-0.5 rounded-md transition-colors ${cameraView === "iso" ? "bg-card text-foreground font-medium" : "text-muted-foreground hover:text-foreground"}`}
            >
              Iso
            </button>
            <button
              onClick={() => handleSetView("front")}
              className={`text-[11px] px-2 py-0.5 rounded-md transition-colors ${cameraView === "front" ? "bg-card text-foreground font-medium" : "text-muted-foreground hover:text-foreground"}`}
            >
              Front
            </button>
            <button
              onClick={() => handleSetView("top")}
              className={`text-[11px] px-2 py-0.5 rounded-md transition-colors ${cameraView === "top" ? "bg-card text-foreground font-medium" : "text-muted-foreground hover:text-foreground"}`}
            >
              Top
            </button>
          </div>

          <Button
            size="sm"
            variant="ghost"
            className={`h-7 px-2 text-xs ${wireframe ? "text-cyan-400 bg-cyan-500/10" : "text-muted-foreground"}`}
            onClick={() => setWireframe((prev) => !prev)}
            title="Toggle Wireframe Overlay"
          >
            <Layers className="w-3.5 h-3.5 mr-1" />
            Wireframe
          </Button>

          <Button
            size="sm"
            variant="ghost"
            className={`h-7 px-2 text-xs ${autoRotate ? "text-primary bg-primary/10" : "text-muted-foreground"}`}
            onClick={() => setAutoRotate((prev) => !prev)}
            title="Toggle Turntable Rotation"
          >
            <RotateCw className="w-3.5 h-3.5 mr-1" />
            Turntable
          </Button>
        </div>
      </div>

      {/* 3D WebGL Canvas Viewport */}
      <div ref={containerRef} className="w-full flex-1 min-h-[440px] cursor-grab active:cursor-grabbing" />

      {/* Bottom Telemetry Bar */}
      <div className="px-4 py-2 bg-card/70 backdrop-blur-md border-t border-border flex items-center justify-between text-[11px] text-muted-foreground">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-foreground font-medium">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            Beveled Procedural PBR Shader
          </span>
          <span>•</span>
          <span>Studio 3-Point Light Matrix</span>
        </div>
        <span className="font-mono text-[10px] text-muted-foreground/60">WebGL 2.0 • 60 FPS</span>
      </div>
    </div>
  );
}
