import {ReactNode} from "react";
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from "remotion";
import {shadowToCss, tokens} from "../theme/tokens";

type ProgrammaticBrollProps = {
  name?: string;
  fallbackName?: string;
};

const baseCardStyle = {
  borderRadius: tokens.radii.md,
  border: "1px solid rgba(198, 226, 255, 0.24)",
  background:
    "linear-gradient(160deg, rgba(8, 16, 35, 0.88), rgba(9, 19, 42, 0.66) 58%, rgba(7, 16, 34, 0.84))",
  boxShadow: `${shadowToCss(tokens.shadows.soft)}, inset 0 1px 0 rgba(255,255,255,0.06)`,
  backdropFilter: "blur(10px)",
};

const titleStyle = {
  margin: 0,
  color: "#f2f7ff",
  fontFamily: tokens.typography.fontFamilySans,
  fontSize: 40,
  fontWeight: 720,
  letterSpacing: 0.12,
  lineHeight: 1.08,
};

const subTitleStyle = {
  margin: 0,
  color: "#dfeeff",
  fontFamily: tokens.typography.fontFamilySans,
  fontSize: 30,
  fontWeight: 620,
  letterSpacing: 0.12,
  lineHeight: 1.1,
};

const copyStyle = {
  margin: 0,
  color: tokens.colors.textMuted,
  fontFamily: tokens.typography.fontFamilySans,
  fontSize: 24,
  lineHeight: 1.3,
};

const microCopyStyle = {
  margin: 0,
  color: tokens.colors.textMuted,
  fontFamily: tokens.typography.fontFamilySans,
  fontSize: 21,
  lineHeight: 1.3,
};

const pillStyle = (active: boolean) => ({
  padding: "8px 14px",
  borderRadius: 999,
  border: `1px solid ${active ? "rgba(255,217,120,0.65)" : "rgba(163,214,255,0.38)"}`,
  backgroundColor: active ? "rgba(255,217,120,0.17)" : "rgba(63,89,132,0.31)",
  color: active ? tokens.colors.accent : "#e1eeff",
  fontFamily: tokens.typography.fontFamilySans,
  fontSize: 21,
  fontWeight: 680,
  letterSpacing: 0.15,
  lineHeight: 1,
});

const chooseVariant = (name?: string, fallbackName?: string): string => {
  const first = name?.trim();
  if (first) {
    return first;
  }
  const second = fallbackName?.trim();
  if (second) {
    return second;
  }
  return "PipelineBlocksBroll";
};

const Box = ({children, padding = 26}: {children: ReactNode; padding?: number}) => (
  <div
    style={{
      ...baseCardStyle,
      padding,
      display: "flex",
      flexDirection: "column",
      gap: 14,
      minWidth: 0,
      overflow: "hidden",
    }}
  >
    {children}
  </div>
);

const Badge = ({label, accent = false}: {label: string; accent?: boolean}) => (
  <div
    style={{
      ...pillStyle(accent),
      maxWidth: "100%",
      whiteSpace: "nowrap",
      overflow: "hidden",
      textOverflow: "ellipsis",
    }}
  >
    {label}
  </div>
);

const KeywordVsMeaning = ({frame}: {frame: number}) => {
  const split = interpolate(frame, [0, 16], [0.96, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gridTemplateRows: "1fr",
        gap: 22,
        transform: `scale(${split})`,
        height: "100%",
      }}
    >
      <Box>
        <p style={titleStyle}>Keyword Search</p>
        <div style={{display: "flex", flexWrap: "wrap", gap: 10}}>
          <Badge label="puppy" accent />
          <Badge label="dog missing" />
          <Badge label="word mismatch" />
        </div>
        <p style={copyStyle}>Matches exact tokens. Synonyms often drop recall.</p>
      </Box>

      <Box>
        <p style={titleStyle}>Vector Search</p>
        <div style={{display: "flex", flexWrap: "wrap", gap: 10}}>
          <Badge label="puppy ~ dog" accent />
          <Badge label="intent match" accent />
          <Badge label="semantic recall" accent />
        </div>
        <p style={copyStyle}>Finds nearby meaning in embedding space.</p>
      </Box>
    </div>
  );
};

const VectorMap = ({frame}: {frame: number}) => {
  const satellites = [
    {x: 22, y: 24, label: "dog", color: "#73b4ff"},
    {x: 28, y: 43, label: "puppy", color: "#73b4ff"},
    {x: 35, y: 62, label: "pet", color: "#73b4ff"},
    {x: 63, y: 19, label: "reset", color: "#44e6d8"},
    {x: 76, y: 34, label: "security", color: "#44e6d8"},
    {x: 70, y: 67, label: "support", color: "#ffd978"},
    {x: 56, y: 74, label: "help", color: "#ffd978"},
  ];

  return (
    <div
      style={{
        ...baseCardStyle,
        height: "100%",
        position: "relative",
        overflow: "hidden",
        background:
          "radial-gradient(circle at 18% 24%, rgba(115,180,255,0.2), transparent 44%), radial-gradient(circle at 72% 72%, rgba(68,230,216,0.18), transparent 46%), rgba(8,15,32,0.75)",
      }}
    >
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        style={{position: "absolute", inset: "8% 6%", width: "88%", height: "84%", opacity: 0.45}}
      >
        {satellites.map((s) => (
          <line
            key={`line-${s.label}`}
            x1={50}
            y1={50}
            x2={s.x}
            y2={s.y}
            stroke="rgba(173,214,255,0.45)"
            strokeWidth="0.55"
          />
        ))}
      </svg>

      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          width: 152,
          height: 152,
          marginLeft: -76,
          marginTop: -76,
          borderRadius: 999,
          border: "2px solid rgba(255,217,120,0.7)",
          backgroundColor: "rgba(255,217,120,0.12)",
          boxShadow: "0 0 30px rgba(255,217,120,0.24)",
          display: "grid",
          placeItems: "center",
          transform: `scale(${0.98 + Math.sin(frame / 12) * 0.03})`,
        }}
      >
        <span style={{...subTitleStyle, fontSize: 24, color: "#ffe8ad"}}>query intent</span>
      </div>

      {[1, 2].map((ring) => (
        <div
          key={`ring-${ring}`}
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            width: 190 + ring * 70,
            height: 190 + ring * 70,
            marginLeft: -(190 + ring * 70) / 2,
            marginTop: -(190 + ring * 70) / 2,
            borderRadius: 999,
            border: "1px dashed rgba(163,214,255,0.22)",
            opacity: 0.7 - ring * 0.2,
          }}
        />
      ))}

      {satellites.map((p, idx) => {
        const amp = 0.96 + Math.sin((frame + idx * 7) / 11) * 0.05;
        return (
          <div
            key={`pt-${p.label}`}
            style={{
              position: "absolute",
              left: `${p.x}%`,
              top: `${p.y}%`,
              transform: `translate(-50%, -50%) scale(${amp})`,
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <div
              style={{
                width: 18,
                height: 18,
                borderRadius: 999,
                backgroundColor: p.color,
                boxShadow: `0 0 14px ${p.color}`,
              }}
            />
            <span style={{...microCopyStyle, fontSize: 17, color: "#dceaff"}}>{p.label}</span>
          </div>
        );
      })}

      <div
        style={{
          position: "absolute",
          left: "6%",
          right: "6%",
          bottom: "8%",
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 10,
        }}
      >
        {["close = similar", "far = different", "query pulls neighbors"].map((label, idx) => (
          <div
            key={`legend-${label}`}
            style={{
              borderRadius: 12,
              border: "1px solid rgba(173,214,255,0.28)",
              background: idx === 2 ? "rgba(255,217,120,0.16)" : "rgba(8,20,42,0.6)",
              padding: "8px 10px",
            }}
          >
            <p style={{...microCopyStyle, fontSize: 16, color: idx === 2 ? "#ffe8ad" : "#dceaff"}}>
              {label}
            </p>
          </div>
        ))}
      </div>

      <div style={{position: "absolute", left: "4.5%", top: "4.5%"}}>
        <p style={{...titleStyle, fontSize: 30}}>Similarity Space</p>
        <p style={{...microCopyStyle}}>closer nodes = closer meaning</p>
      </div>
    </div>
  );
};

const Chunks = ({frame}: {frame: number}) => {
  const shift = interpolate(frame, [0, 16], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const cards = ["Chunk A", "Chunk B", "Chunk C", "Chunk D"];

  return (
    <div style={{display: "grid", gridTemplateColumns: "1.05fr 1.55fr", gap: 20, alignItems: "stretch"}}>
      <Box>
        <p style={titleStyle}>Split Content</p>
        <p style={copyStyle}>Break docs into small semantic units before embedding.</p>
        <div style={{display: "grid", gap: 8}}>
          <p style={microCopyStyle}>- Support article</p>
          <p style={microCopyStyle}>- Product notes</p>
          <p style={microCopyStyle}>- Chat transcript</p>
        </div>
      </Box>

      <div style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12}}>
        {cards.map((c, i) => (
          <div
            key={c}
            style={{
              ...baseCardStyle,
              padding: 16,
              transform: `translateY(${shift * Math.max(0, 1 - i * 0.2)}px)`,
              display: "grid",
              gap: 8,
              minHeight: 166,
            }}
          >
            <p style={{...subTitleStyle}}>{c}</p>
            <p style={{...microCopyStyle, fontSize: 18}}>self-contained meaning block</p>
          </div>
        ))}
      </div>
    </div>
  );
};

const Embeddings = ({frame}: {frame: number}) => {
  const bars = [0.82, 0.26, 0.63, 0.44, 0.74, 0.39];

  return (
    <div style={{display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: 20, alignItems: "stretch"}}>
      <Box>
        <p style={titleStyle}>Embedding Model</p>
        <p style={copyStyle}>Turns text chunks into vectors that encode semantics.</p>
        <div
          style={{
            marginTop: 4,
            width: "100%",
            minHeight: 172,
            borderRadius: 14,
            border: "1px solid rgba(163,214,255,0.26)",
            background: "rgba(9,18,36,0.7)",
            display: "grid",
            placeItems: "center",
          }}
        >
          <div style={{position: "relative", width: 180, height: 180}}>
            {[0, 1, 2].map((ring) => (
              <div
                key={`embed-ring-${ring}`}
                style={{
                  position: "absolute",
                  left: "50%",
                  top: "50%",
                  width: 58 + ring * 48,
                  height: 58 + ring * 48,
                  marginLeft: -(58 + ring * 48) / 2,
                  marginTop: -(58 + ring * 48) / 2,
                  borderRadius: 999,
                  border: "1px solid rgba(173,214,255,0.3)",
                  opacity: 0.8 - ring * 0.18,
                }}
              />
            ))}
            <div
              style={{
                position: "absolute",
                left: "50%",
                top: "50%",
                marginLeft: -18,
                marginTop: -18,
                width: 36,
                height: 36,
                borderRadius: 999,
                backgroundColor: "rgba(255,217,120,0.82)",
                transform: `scale(${0.94 + Math.sin(frame / 10) * 0.08})`,
              }}
            />
          </div>
        </div>
      </Box>

      <Box>
        <p style={titleStyle}>Vector Dimensions</p>
        <div style={{display: "grid", gap: 10, marginTop: 6}}>
          {bars.map((v, idx) => {
            const pulse = 0.97 + Math.sin((frame + idx * 8) / 13) * 0.06;
            return (
              <div key={`bar-${idx}`} style={{display: "grid", gridTemplateColumns: "102px 1fr", gap: 10, alignItems: "center"}}>
                <p style={{...microCopyStyle, fontSize: 18, margin: 0}}>dim_{idx + 1}</p>
                <div style={{height: 13, borderRadius: 999, backgroundColor: "rgba(83,108,148,0.45)", overflow: "hidden"}}>
                  <div
                    style={{
                      height: "100%",
                      width: `${Math.round(v * 100)}%`,
                      borderRadius: 999,
                      background:
                        "linear-gradient(90deg, rgba(115,180,255,0.9), rgba(68,230,216,0.74))",
                      transform: `scaleX(${pulse})`,
                      transformOrigin: "left center",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </Box>
    </div>
  );
};

const StoreAndLink = () => {
  const rows = [
    ["v_1024", "faq/reset-password"],
    ["v_1025", "help/account-security"],
    ["v_1026", "guide/sign-in-troubleshoot"],
    ["v_1027", "docs/mfa-recovery"],
  ];

  return (
    <Box padding={22}>
      <p style={titleStyle}>Vector Store + Source Link</p>
      <div style={{display: "grid", gap: 10}}>
        {rows.map((r, idx) => (
          <div
            key={r[0]}
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(130px, 0.95fr) 32px minmax(0, 2fr)",
              alignItems: "center",
              borderRadius: 12,
              border: "1px solid rgba(163,214,255,0.24)",
              padding: "10px 12px",
              color: "#e7f0ff",
              fontFamily: tokens.typography.fontFamilySans,
              fontSize: 21,
              columnGap: 10,
              minWidth: 0,
              backgroundColor: idx % 2 === 0 ? "rgba(10,20,38,0.45)" : "rgba(10,20,38,0.24)",
            }}
          >
            <span style={{overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap"}}>{r[0]}</span>
            <span style={{opacity: 0.74}}>-&gt;</span>
            <span
              style={{
                color: tokens.colors.secondary,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                fontSize: 20,
              }}
            >
              {r[1]}
            </span>
          </div>
        ))}
      </div>
    </Box>
  );
};

const NearestNeighbors = ({frame}: {frame: number}) => {
  const hits = [
    {title: "Reset password in account center", score: 0.93},
    {title: "I cannot sign in after update", score: 0.88},
    {title: "Two-factor recovery options", score: 0.84},
  ];

  return (
    <div style={{display: "grid", gridTemplateColumns: "1fr 1.15fr", gap: 20}}>
      <Box>
        <p style={titleStyle}>Query Embedding</p>
        <div
          style={{
            ...baseCardStyle,
            borderStyle: "dashed",
            padding: 16,
            backgroundColor: "rgba(12,22,42,0.62)",
          }}
        >
          <p style={{...copyStyle, color: "#f5fbff"}}>&quot;How do I reset my password?&quot;</p>
        </div>
        <p style={microCopyStyle}>vectorized and compared with nearest stored vectors</p>
      </Box>

      <Box>
        <p style={titleStyle}>Top Matches</p>
        <div style={{display: "grid", gap: 10}}>
          {hits.map((h, idx) => {
            const scoreW = Math.max(20, Math.round(h.score * 100));
            const pulse = 0.98 + Math.sin((frame + idx * 10) / 15) * 0.04;
            return (
              <div key={h.title} style={{display: "grid", gap: 7}}>
                <div style={{display: "flex", justifyContent: "space-between", gap: 8}}>
                  <p
                    style={{
                      ...microCopyStyle,
                      fontSize: 19,
                      margin: 0,
                      color: "#e8f2ff",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {idx + 1}. {h.title}
                  </p>
                  <p style={{...microCopyStyle, margin: 0, color: "#9fd7ff"}}>{Math.round(h.score * 100)}%</p>
                </div>
                <div style={{height: 9, borderRadius: 999, backgroundColor: "rgba(83,108,148,0.45)", overflow: "hidden"}}>
                  <div
                    style={{
                      height: "100%",
                      width: `${scoreW}%`,
                      borderRadius: 999,
                      background: "linear-gradient(90deg, rgba(255,217,120,0.88), rgba(68,230,216,0.72))",
                      transform: `scaleX(${pulse})`,
                      transformOrigin: "left center",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </Box>
    </div>
  );
};

const UseCasesIcons = ({frame}: {frame: number}) => {
  const items = [
    {title: "Semantic Search", copy: "find by intent", icon: "search"},
    {title: "Chatbot Recall", copy: "grounded answers", icon: "chat"},
    {title: "Docs Q and A", copy: "retrieval first", icon: "docs"},
  ];

  return (
    <div style={{display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16}}>
      {items.map((item, idx) => {
        const pulse = 0.96 + Math.sin((frame + idx * 11) / 16) * 0.06;
        return (
          <Box key={item.title}>
            <div
              style={{
                width: 72,
                height: 72,
                borderRadius: 999,
                border: "2px solid rgba(163,214,255,0.6)",
                background:
                  "radial-gradient(circle at 30% 30%, rgba(115,180,255,0.58), rgba(68,230,216,0.34))",
                transform: `scale(${pulse})`,
                display: "grid",
                placeItems: "center",
              }}
            >
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: item.icon === "docs" ? 6 : 999,
                  border: "2px solid rgba(245,252,255,0.92)",
                }}
              />
            </div>
            <p style={{...subTitleStyle, fontSize: 27}}>{item.title}</p>
            <p style={{...copyStyle, fontSize: 20}}>{item.copy}</p>
          </Box>
        );
      })}
    </div>
  );
};

const RetrieveThenAnswer = () => {
  const steps = [
    {title: "Retrieve", copy: "fetch relevant facts"},
    {title: "Rerank", copy: "pick best evidence"},
    {title: "Answer", copy: "respond with context"},
  ];

  return (
    <div style={{display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14, alignItems: "stretch"}}>
      {steps.map((s, idx) => (
        <div key={s.title} style={{display: "grid", gridTemplateColumns: "1fr auto", alignItems: "center", gap: 8}}>
          <div style={{...baseCardStyle, padding: 18, minHeight: 210, display: "grid", alignContent: "center", gap: 12}}>
            <p style={{...titleStyle, fontSize: 31}}>{s.title}</p>
            <p style={{...copyStyle, fontSize: 20}}>{s.copy}</p>
          </div>
          {idx < steps.length - 1 ? (
            <span style={{color: tokens.colors.secondary, fontFamily: tokens.typography.fontFamilySans, fontSize: 34}}>-&gt;</span>
          ) : null}
        </div>
      ))}
    </div>
  );
};

const CatalogCards = () => {
  const cards = [
    "Running Shoes",
    "Gaming Mouse",
    "Office Chair",
    "Wireless Earbuds",
    "Coffee Grinder",
    "Travel Backpack",
  ];

  return (
    <div style={{display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12}}>
      {cards.map((c, idx) => (
        <div key={c} style={{...baseCardStyle, padding: 14, minHeight: 132, display: "grid", gap: 8}}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: idx % 2 === 0 ? 999 : 9,
              backgroundColor: "rgba(115,180,255,0.5)",
            }}
          />
          <p
            style={{
              ...subTitleStyle,
              fontSize: 22,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {c}
          </p>
          <div style={{display: "flex", gap: 6, flexWrap: "wrap"}}>
            <Badge label="intent" />
            <Badge label="similar" />
          </div>
        </div>
      ))}
    </div>
  );
};

const PipelineBlocks = ({frame}: {frame: number}) => {
  const blocks = ["Chunk", "Embed", "Store", "Search", "Answer"];

  return (
    <div style={{display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, alignItems: "center"}}>
      {blocks.map((block, idx) => (
        <div key={block} style={{display: "grid", gridTemplateColumns: "1fr auto", alignItems: "center", gap: 8}}>
          <div style={{...baseCardStyle, padding: "16px 10px", textAlign: "center", minHeight: 110}}>
            <p style={{...subTitleStyle, fontSize: 25}}>{block}</p>
            <div
              style={{
                marginTop: 8,
                height: 8,
                borderRadius: 999,
                background:
                  "linear-gradient(90deg, rgba(115,180,255,0.7), rgba(68,230,216,0.65))",
                transform: `scaleX(${0.95 + Math.sin((frame + idx * 7) / 14) * 0.05})`,
                transformOrigin: "left center",
              }}
            />
          </div>
          {idx < blocks.length - 1 ? <span style={{color: "#c6e4ff", fontSize: 30}}>-&gt;</span> : null}
        </div>
      ))}
    </div>
  );
};

const SearchIcon = ({frame}: {frame: number}) => {
  return (
    <div style={{display: "grid", gridTemplateColumns: "280px 1fr", gap: 20, alignItems: "center"}}>
      <div
        style={{
          ...baseCardStyle,
          height: 280,
          display: "grid",
          placeItems: "center",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {[0, 1].map((ring) => (
          <div
            key={`lens-ring-${ring}`}
            style={{
              position: "absolute",
              width: 96 + ring * 40,
              height: 96 + ring * 40,
              borderRadius: 999,
              border: "1px solid rgba(173,214,255,0.3)",
            }}
          />
        ))}

        <div
          style={{
            width: 104,
            height: 104,
            borderRadius: 999,
            border: "8px solid rgba(115,180,255,0.86)",
            position: "relative",
            transform: `scale(${0.95 + Math.sin(frame / 11) * 0.05})`,
          }}
        >
          <div
            style={{
              position: "absolute",
              right: -24,
              bottom: -24,
              width: 48,
              height: 9,
              transform: "rotate(45deg)",
              borderRadius: 999,
              backgroundColor: "rgba(68,230,216,0.86)",
            }}
          />
        </div>
      </div>

      <Box>
        <p style={titleStyle}>Semantic Retrieval</p>
        <p style={copyStyle}>Query embedding compares with nearest candidates in vector space.</p>
        <div style={{display: "flex", gap: 10, flexWrap: "wrap"}}>
          <Badge label="distance" accent />
          <Badge label="neighbors" accent />
          <Badge label="recall" accent />
        </div>
      </Box>
    </div>
  );
};

const DashboardIcons = ({frame}: {frame: number}) => {
  const items = ["Tickets", "Notes", "Catalog", "Chats", "FAQ", "Guides"];

  return (
    <div style={{display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12}}>
      {items.map((i, idx) => (
        <Box key={i} padding={18}>
          <div style={{display: "flex", gap: 7}}>
            {[0, 1, 2].map((d) => (
              <div
                key={`${i}-dot-${d}`}
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: 999,
                  backgroundColor: d === 1 ? "rgba(255,217,120,0.65)" : "rgba(115,180,255,0.42)",
                  transform: `scale(${0.95 + Math.sin((frame + idx * 6 + d * 4) / 13) * 0.08})`,
                }}
              />
            ))}
          </div>
          <p style={{...subTitleStyle, fontSize: 23}}>{i}</p>
          <p style={{...microCopyStyle}}>meaning-aware lookup</p>
        </Box>
      ))}
    </div>
  );
};

const SemanticOrbit = ({frame}: {frame: number}) => {
  const labels = [
    {key: "query", tone: "primary"},
    {key: "intent", tone: "secondary"},
    {key: "vector", tone: "primary"},
    {key: "context", tone: "secondary"},
    {key: "match", tone: "primary"},
    {key: "answer", tone: "secondary"},
  ] as const;
  const chips = ["semantic recall", "nearest meaning", "intent first"];

  return (
    <div style={{display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: 18, height: "100%"}}>
      <Box>
        <p style={titleStyle}>Meaning Space</p>
        <p style={copyStyle}>Keywords can drift. Dense vectors keep related ideas near each other.</p>
        <div style={{display: "grid", gap: 8, marginTop: 8}}>
          <p style={microCopyStyle}>- cluster by semantic distance</p>
          <p style={microCopyStyle}>- map query to same space</p>
          <p style={microCopyStyle}>- retrieve closest evidence</p>
        </div>
        <div style={{display: "flex", flexWrap: "wrap", gap: 8, marginTop: 6}}>
          {chips.map((chip, idx) => (
            <Badge key={chip} label={chip} accent={idx !== 1} />
          ))}
        </div>
      </Box>

      <div
        style={{
          ...baseCardStyle,
          position: "relative",
          height: "100%",
          minHeight: 420,
          overflow: "hidden",
          background:
            "radial-gradient(circle at 32% 30%, rgba(115,180,255,0.22), transparent 44%), radial-gradient(circle at 72% 72%, rgba(68,230,216,0.2), transparent 48%), linear-gradient(160deg, rgba(8, 16, 35, 0.9), rgba(8, 18, 39, 0.68))",
        }}
      >
        {[0, 1, 2].map((ring) => (
          <div
            key={`orbit-ring-${ring}`}
            style={{
              position: "absolute",
              left: "50%",
              top: "50%",
              width: 200 + ring * 116,
              height: 200 + ring * 116,
              marginLeft: -(200 + ring * 116) / 2,
              marginTop: -(200 + ring * 116) / 2,
              borderRadius: 999,
              border: "1px solid rgba(163,214,255,0.28)",
              opacity: 0.95 - ring * 0.18,
            }}
          />
        ))}

        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            width: 190,
            height: 190,
            marginLeft: -95,
            marginTop: -95,
            borderRadius: 999,
            border: "2px solid rgba(255,217,120,0.72)",
            backgroundColor: "rgba(255,217,120,0.12)",
            display: "grid",
            placeItems: "center",
            boxShadow: "0 0 38px rgba(255,217,120,0.24)",
            transform: `scale(${0.96 + Math.sin(frame / 11) * 0.06})`,
          }}
        >
          <p
            style={{
              ...subTitleStyle,
              fontSize: 40,
              color: "#ffe8ad",
              textAlign: "center",
              whiteSpace: "pre-line",
            }}
          >
            meaning{"\n"}core
          </p>
        </div>

        {labels.map((label, idx) => {
          const angle = (idx / labels.length) * Math.PI * 2 + frame * 0.008;
          const radius = 190 + (idx % 2) * 88;
          const cx = 50 + (Math.cos(angle) * radius) / 9.8;
          const cy = 50 + (Math.sin(angle) * radius) / 6.8;
          return (
            <div
              key={label.key}
              style={{
                position: "absolute",
                left: `${cx}%`,
                top: `${cy}%`,
                transform: "translate(-50%, -50%)",
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "7px 10px",
                borderRadius: 999,
                border: "1px solid rgba(163,214,255,0.24)",
                backgroundColor: "rgba(7, 16, 35, 0.74)",
              }}
            >
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: 999,
                  backgroundColor: label.tone === "primary" ? "#73b4ff" : "#44e6d8",
                  boxShadow:
                    label.tone === "primary"
                      ? "0 0 10px rgba(115,180,255,0.5)"
                      : "0 0 10px rgba(68,230,216,0.5)",
                }}
              />
              <span style={{...microCopyStyle, fontSize: 20, color: "#dbeaff"}}>{label.key}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const renderByVariant = (variant: string, frame: number): ReactNode => {
  switch (variant) {
    case "KeywordVsMeaningBroll":
      return <KeywordVsMeaning frame={frame} />;
    case "VectorMapBroll":
      return <VectorMap frame={frame} />;
    case "ChunksBroll":
      return <Chunks frame={frame} />;
    case "EmbeddingsBroll":
      return <Embeddings frame={frame} />;
    case "StoreAndLinkBroll":
      return <StoreAndLink />;
    case "NearestNeighborsBroll":
      return <NearestNeighbors frame={frame} />;
    case "UseCasesIconsBroll":
      return <UseCasesIcons frame={frame} />;
    case "RetrieveThenAnswerBroll":
      return <RetrieveThenAnswer />;
    case "CatalogCardsBroll":
      return <CatalogCards />;
    case "SearchIconBroll":
      return <SearchIcon frame={frame} />;
    case "DashboardIconsBroll":
      return <DashboardIcons frame={frame} />;
    case "SemanticOrbitBroll":
      return <SemanticOrbit frame={frame} />;
    case "PipelineBlocksBroll":
    default:
      return <PipelineBlocks frame={frame} />;
  }
};

export const ProgrammaticBroll = ({name, fallbackName}: ProgrammaticBrollProps) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const variant = chooseVariant(name, fallbackName);

  const inOpacity = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const inY = interpolate(frame, [0, 14], [24, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        opacity: inOpacity,
        transform: `translateY(${inY}px)`,
      }}
    >
      <div
        style={{
          position: "absolute",
          left: Math.round(width * 0.03),
          right: Math.round(width * 0.03),
          top: Math.round(height * 0.06),
          bottom: Math.round(height * 0.06),
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: Math.round(width * 0.96),
            height: Math.round(height * 0.82),
            minWidth: 0,
            maxHeight: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              width: "100%",
              minWidth: 0,
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {renderByVariant(variant, frame)}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
