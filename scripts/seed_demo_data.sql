-- ==============================================================================
-- SOCMINT Academic Research Prototype — Offline Demo Seed Data
-- 30 Curated Channels | Historical Space & Defense Discourse | Multi-dialectal
-- ==============================================================================

BEGIN;

-- 1. Ensure Monitored Channels Registry (30 Curated Channels)
INSERT INTO monitored_channels (identifier, display_name, topic_tags, is_active, last_polled_at, last_polled_message_id)
VALUES
  ('@isro_updates', 'ISRO Official News & Launch Updates', '["space", "ISRO", "satellite", "technology"]'::jsonb, true, NOW(), 1001),
  ('@indianspace_discussion', 'Indian Space Discussion Group', '["space", "ISRO", "chandrayaan", "gaganyaan"]'::jsonb, true, NOW(), 1002),
  ('@isrospaceupdates', 'ISRO Space Missions & Payload Tracker', '["space", "payload", "launch_vehicle", "PSLV"]'::jsonb, true, NOW(), 1003),
  ('@indianspaceresearch', 'Indian Space Research Community', '["space", "astronomy", "research", "IN-SPACe"]'::jsonb, true, NOW(), 1004),
  ('@gaganyaan_mission', 'Gaganyaan Human Spaceflight Forum', '["space", "gaganyaan", "astronauts", "human_spaceflight"]'::jsonb, true, NOW(), 1005),
  ('@space_india_portal', 'Space India Public Portal', '["space", "education", "satellite", "policy"]'::jsonb, true, NOW(), 1006),
  ('@drdo_updates', 'DRDO Technology Bulletin', '["defense", "DRDO", "indigenous", "missiles"]'::jsonb, true, NOW(), 1007),
  ('@indiandefenceupdate', 'Indian Defence News & Modernization', '["defense", "military", "modernization", "security"]'::jsonb, true, NOW(), 1008),
  ('@defencenewsindia', 'Defence Updates India', '["defense", "army", "navy", "airforce"]'::jsonb, true, NOW(), 1009),
  ('@aerospace_defence_india', 'Aerospace & Defense India', '["aerospace", "aviation", "Tejas", "AMCA"]'::jsonb, true, NOW(), 1010),
  ('@idrw_org', 'Indian Defence Research Wing (IDRW)', '["defense", "military_analysis", "research", "procurement"]'::jsonb, true, NOW(), 1011),
  ('@bharat_defence', 'Bharat Defence Forum', '["defense", "atmanirbhar", "security", "geopolitics"]'::jsonb, true, NOW(), 1012),
  ('@strategic_affairs_in', 'Indian Strategic Affairs & Security', '["geopolitics", "security", "strategy", "foreign_policy"]'::jsonb, true, NOW(), 1013),
  ('@geopolitics_india', 'South Asia Geopolitics Desk', '["geopolitics", "border", "maritime", "diplomacy"]'::jsonb, true, NOW(), 1014),
  ('@indiadiplomacy', 'India Diplomacy & External Affairs', '["diplomacy", "MEA", "bilateral", "global_affairs"]'::jsonb, true, NOW(), 1015),
  ('@southasiandefence', 'South Asian Defence Analysis', '["geopolitics", "defense", "regional_security"]'::jsonb, true, NOW(), 1016),
  ('@stratfront', 'Strategic Frontier Watch', '["national_security", "cyber", "space_defense", "tactics"]'::jsonb, true, NOW(), 1017),
  ('@indiastrategic', 'India Strategic Review', '["policy", "defense", "military", "aerospace"]'::jsonb, true, NOW(), 1018),
  ('@csir_india', 'CSIR Science & Innovation Bulletin', '["science", "innovation", "CSIR", "laboratories"]'::jsonb, true, NOW(), 1019),
  ('@indiatechpolicy', 'India Tech Policy & Semiconductor Desk', '["technology", "semiconductor", "AI_policy", "telecom"]'::jsonb, true, NOW(), 1020),
  ('@vigyanprasar', 'Vigyan Prasar Science Communications', '["science", "popular_science", "stem", "education"]'::jsonb, true, NOW(), 1021),
  ('@digital_india_news', 'Digital India Technology Tracker', '["technology", "telecom", "5G", "digital_governance"]'::jsonb, true, NOW(), 1022),
  ('@meity_updates', 'MeitY Technology & Cyber Bulletin', '["cybersecurity", "MeitY", "DPDP", "CERT-In"]'::jsonb, true, NOW(), 1023),
  ('@quantum_mission_india', 'National Quantum Mission Updates', '["technology", "quantum", "computing", "R&D"]'::jsonb, true, NOW(), 1024),
  ('@frontierindia', 'Frontier India Technology & Defense', '["defense", "space", "nuclear", "maritime"]'::jsonb, true, NOW(), 1025),
  ('@defence_forum_india', 'Defence Forum India Discussion', '["defense", "forum", "community", "discourse"]'::jsonb, true, NOW(), 1026),
  ('@indiannavy_updates', 'Indian Maritime & Naval Tech', '["navy", "maritime", "indigenous_ships", "defense"]'::jsonb, true, NOW(), 1027),
  ('@iaf_updates_hub', 'Indian Air Force Aviation Hub', '["airforce", "aviation", "fighters", "defense"]'::jsonb, true, NOW(), 1028),
  ('@criticaltech_india', 'Critical Technologies Watch', '["technology", "space", "defense", "critical_minerals"]'::jsonb, true, NOW(), 1029),
  ('@space_defence_hub', 'Space & Defense Intelligence Hub', '["space", "defense", "satellites", "military_space"]'::jsonb, true, NOW(), 1030)
ON CONFLICT (identifier) DO NOTHING;

-- 2. Create Initial Offline Demo Ingestion Run
INSERT INTO ingestion_runs (id, started_at, completed_at, platform, channel_ids, posts_collected, status)
VALUES (
  '00000000-0000-0000-0000-000000000001'::uuid,
  NOW() - INTERVAL '48 hours',
  NOW() - INTERVAL '47 hours',
  'telegram',
  '["@isro_updates", "@indianspace_discussion", "@drdo_updates", "@indiandefenceupdate", "@geopolitics_india"]'::jsonb,
  35,
  'completed'
)
ON CONFLICT (id) DO NOTHING;

-- 3. Seed Realistic Author Profiles for Discussion & Demographic Sampling
INSERT INTO raw_authors (platform, platform_author_id, display_name, bio_text, follower_count, account_created_at, snapshot_at, ingestion_run_id)
VALUES
  ('telegram', 'user_101', 'Aarav Sharma', 'Aerospace engineer & space policy enthusiast | Bengaluru', 120, '2022-01-15'::timestamptz, NOW(), '00000000-0000-0000-0000-000000000001'::uuid),
  ('telegram', 'user_102', 'Vikramaditya', 'Defense analyst, ex-IAF enthusiast. Tracking indigenization | New Delhi', 450, '2021-06-10'::timestamptz, NOW(), '00000000-0000-0000-0000-000000000001'::uuid),
  ('telegram', 'user_103', 'Priya_Tech', 'VLSI designer, semiconductor policy watcher | Hyderabad', 85, '2023-03-20'::timestamptz, NOW(), '00000000-0000-0000-0000-000000000001'::uuid),
  ('telegram', 'user_104', 'Sanjay Verma', 'Geopolitics scholar, maritime strategist | Mumbai', 310, '2020-11-05'::timestamptz, NOW(), '00000000-0000-0000-0000-000000000001'::uuid),
  ('telegram', 'user_105', 'Rohan_K', 'ISRO watcher, astrophysics student | Chennai', 95, '2023-09-01'::timestamptz, NOW(), '00000000-0000-0000-0000-000000000001'::uuid),
  ('telegram', 'user_106', 'Meera Iyer', 'Telecom researcher, digital rights & cybersecurity | Pune', 210, '2022-04-18'::timestamptz, NOW(), '00000000-0000-0000-0000-000000000001'::uuid),
  ('telegram', 'user_107', 'DesiStrategist', 'Tracking South Asian balance of power and deterrence', 540, '2021-08-22'::timestamptz, NOW(), '00000000-0000-0000-0000-000000000001'::uuid),
  ('telegram', 'user_108', 'Ananya Patel', 'Science communicator, space enthusiast | Ahmedabad', 160, '2022-10-12'::timestamptz, NOW(), '00000000-0000-0000-0000-000000000001'::uuid);

-- 4. Seed Multi-Dialectal Raw Posts for Analysis (English + Code-mixed Hinglish)
INSERT INTO raw_posts (
  platform, platform_post_id, channel_id, author_id, content_text, content_language,
  view_count, reaction_counts, ingested_at, posted_at, ingestion_run_id, processing_status
)
VALUES
  -- Post 1: ISRO Official Announcement (Supportive, English)
  ('telegram', 'post_1001', '@isro_updates', NULL,
   'ISRO successfully completes the initial integration phase for the Gaganyaan orbital module. Environmental control and life support systems (ECLSS) simulated performance validated under high pressure parameters.',
   'en', 15400, '{"👍": 2100, "🚀": 1850, "❤️": 920}'::jsonb,
   NOW() - INTERVAL '36 hours', NOW() - INTERVAL '36 hours', '00000000-0000-0000-0000-000000000001'::uuid, 'pending'),

  -- Post 2: Hinglish Enthusiastic Reaction (Joy, Supportive)
  ('telegram', 'post_1002', '@indianspace_discussion', 'user_101',
   'Kamaal ka achievement hai! Gaganyaan life support tests passed successfully. Proud moment for all Indian space engineers! 🇮🇳🚀',
   'hi', 4200, '{"🔥": 340, "👏": 210}'::jsonb,
   NOW() - INTERVAL '35 hours', NOW() - INTERVAL '35 hours', '00000000-0000-0000-0000-000000000001'::uuid, 'pending'),

  -- Post 3: Objective Technical Critique / Mild Skepticism (Neutral Stance)
  ('telegram', 'post_1003', '@indianspace_discussion', 'user_105',
   'ECLSS validation is good, but without human-rated cryogenic upper stage static tests, crewed launch within 2025 timeline looks highly constrained. Need more transparency on TV-D2 launch window.',
   'en', 3100, '{"🤔": 140, "👍": 85}'::jsonb,
   NOW() - INTERVAL '34 hours', NOW() - INTERVAL '34 hours', '00000000-0000-0000-0000-000000000001'::uuid, 'pending'),

  -- Post 4: DRDO Indigenous Trials (Supportive, Pride)
  ('telegram', 'post_1004', '@drdo_updates', NULL,
   'DRDO conducts successful flight test of new generation anti-radiation missile (Rudram-II) from Su-30MKI platform off the east coast of Odisha. All propulsion and precision homing objectives achieved.',
   'en', 18900, '{"🎯": 1450, "🇮🇳": 2900, "👍": 1200}'::jsonb,
   NOW() - INTERVAL '30 hours', NOW() - INTERVAL '30 hours', '00000000-0000-0000-0000-000000000001'::uuid, 'pending'),

  -- Post 5: Hinglish Defense Discussion (Joy / Supportive)
  ('telegram', 'post_1005', '@indiandefenceupdate', 'user_102',
   'Rudram-II testing complete! Indigenous defense R&D steadily replacing imported air-to-surface inventory. Ab SEAD missions mein full self-reliance hoga.',
   'hi', 5600, '{"💪": 410, "🔥": 290}'::jsonb,
   NOW() - INTERVAL '29 hours', NOW() - INTERVAL '29 hours', '00000000-0000-0000-0000-000000000001'::uuid, 'pending'),

  -- Post 6: Sarcastic Post for Advisory Flagging (Valence-Emoji Incongruity, Sarcasm Flag = TRUE)
  ('telegram', 'post_1006', '@defence_forum_india', 'user_107',
   'Wah kya baat hai, brilliant procurement planning! Ten years of tender processing and we still await engine sanctions 🙄🙃🤡 Masterstroke of bureaucratic agility.',
   'hi', 2800, '{"😂": 190, "🙄": 145}'::jsonb,
   NOW() - INTERVAL '26 hours', NOW() - INTERVAL '26 hours', '00000000-0000-0000-0000-000000000001'::uuid, 'pending'),

  -- Post 7: Tech Policy Semiconductor Fab (Excitement / Supportive)
  ('telegram', 'post_1007', '@indiatechpolicy', 'user_103',
   'Dholera semiconductor plant cleanroom construction ahead of schedule. First commercial silicon wafers expected by late 2026. India entering the global fab supply chain is monumental for defense microelectronics.',
   'en', 6100, '{"💡": 320, "🚀": 410, "👍": 280}'::jsonb,
   NOW() - INTERVAL '22 hours', NOW() - INTERVAL '22 hours', '00000000-0000-0000-0000-000000000001'::uuid, 'pending'),

  -- Post 8: Cross-Channel Forward for Network Edge Modeling
  ('telegram', 'post_1008', '@aerospace_defence_india', 'user_102',
   'Forwarding from @isro_updates: Strategic alignment between ISRO space assets and military communications network (GSAT-7R) progressing on schedule for mid-year integration.',
   'en', 3900, '{"🛰️": 280, "👍": 150}'::jsonb,
   NOW() - INTERVAL '18 hours', NOW() - INTERVAL '18 hours', '00000000-0000-0000-0000-000000000001'::uuid, 'pending'),

  -- Post 9: Synchronous Cluster Test 1 (Near-duplicate text for CIB Heuristic detection)
  ('telegram', 'post_1009', '@stratfront', 'user_104',
   'Critical security alert: Unconfirmed foreign cyber probing detected against critical space telemetry infrastructure. Immediate perimeter hardening required.',
   'en', 1200, '{"⚠️": 85}'::jsonb,
   NOW() - INTERVAL '12 hours', NOW() - INTERVAL '12 hours', '00000000-0000-0000-0000-000000000001'::uuid, 'pending'),

  -- Post 10: Synchronous Cluster Test 2 (Same text, different channel, 30s delta)
  ('telegram', 'post_1010', '@defence_forum_india', 'user_107',
   'Critical security alert: Unconfirmed foreign cyber probing detected against critical space telemetry infrastructure. Immediate perimeter hardening required.',
   'en', 1150, '{"⚠️": 70}'::jsonb,
   NOW() - INTERVAL '12 hours' + INTERVAL '30 seconds', NOW() - INTERVAL '12 hours' + INTERVAL '30 seconds', '00000000-0000-0000-0000-000000000001'::uuid, 'pending')
ON CONFLICT (platform, platform_post_id) DO NOTHING;

COMMIT;
