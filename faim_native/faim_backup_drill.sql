--
-- PostgreSQL database dump
--

\restrict uKXwE4QOVTRbb1xaBaGUUjuAhsVnrzoG2SLV7V2wbkjYsXxex7WywGoO27jJ8FG

-- Dumped from database version 15.15 (Debian 15.15-1.pgdg13+1)
-- Dumped by pg_dump version 15.15 (Debian 15.15-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: edges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.edges (
    edge_id uuid NOT NULL,
    tenant_id text NOT NULL,
    graph_id character varying(64) NOT NULL,
    src_node_id uuid NOT NULL,
    dst_node_id uuid NOT NULL,
    kind character varying(32) NOT NULL,
    weight double precision DEFAULT 0.0,
    meta json,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.events (
    seq integer NOT NULL,
    id uuid NOT NULL,
    tenant_id text NOT NULL,
    ts timestamp without time zone NOT NULL,
    graph_id character varying(64) NOT NULL,
    kind character varying(64) NOT NULL,
    payload json DEFAULT '{}'::json,
    checksum character varying(64) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: events_seq_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.events_seq_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: events_seq_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.events_seq_seq OWNED BY public.events.seq;


--
-- Name: graph_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.graph_version (
    tenant_id text NOT NULL,
    graph_id character varying(64) NOT NULL,
    version bigint DEFAULT 0 NOT NULL,
    reason text,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: ingest_dedup; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ingest_dedup (
    tenant_id text NOT NULL,
    graph_id text NOT NULL,
    packet_hash text NOT NULL,
    raw_id uuid,
    node_count integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: job_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_events (
    seq integer NOT NULL,
    job_id uuid NOT NULL,
    ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    kind text NOT NULL,
    payload json DEFAULT '{}'::json NOT NULL
);


--
-- Name: job_events_seq_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.job_events_seq_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: job_events_seq_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.job_events_seq_seq OWNED BY public.job_events.seq;


--
-- Name: jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.jobs (
    job_id uuid NOT NULL,
    tenant_id text NOT NULL,
    graph_id text NOT NULL,
    kind text NOT NULL,
    payload_json json DEFAULT '{}'::json,
    status text DEFAULT 'pending'::text NOT NULL,
    error_message text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    started_at timestamp without time zone,
    completed_at timestamp without time zone
);


--
-- Name: nodes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nodes (
    node_id uuid NOT NULL,
    tenant_id text NOT NULL,
    graph_id character varying(64) NOT NULL,
    kind character varying(16) DEFAULT 'atom'::character varying NOT NULL,
    vector_hash character varying(64) NOT NULL,
    raw_id text,
    block_id text,
    anchor_json json,
    v_native json NOT NULL,
    opp_signature json,
    residual double precision DEFAULT 0.0,
    level integer DEFAULT 0,
    touch_count integer DEFAULT 0,
    last_access timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: raw_refs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_refs (
    id uuid NOT NULL,
    tenant_id text NOT NULL,
    sha256 character varying(64) NOT NULL,
    uri text NOT NULL,
    mime_type character varying(128) DEFAULT 'application/octet-stream'::character varying,
    size_bytes bigint NOT NULL,
    graph_id character varying(64),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    version integer NOT NULL,
    applied_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    checksum text NOT NULL
);


--
-- Name: snapshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.snapshots (
    id uuid NOT NULL,
    tenant_id text NOT NULL,
    graph_id character varying(64) NOT NULL,
    graph_version bigint NOT NULL,
    graph_hash character varying(64) NOT NULL,
    node_count integer DEFAULT 0 NOT NULL,
    metadata json,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: events seq; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events ALTER COLUMN seq SET DEFAULT nextval('public.events_seq_seq'::regclass);


--
-- Name: job_events seq; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_events ALTER COLUMN seq SET DEFAULT nextval('public.job_events_seq_seq'::regclass);


--
-- Data for Name: edges; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.edges (edge_id, tenant_id, graph_id, src_node_id, dst_node_id, kind, weight, meta, created_at) FROM stdin;
\.


--
-- Data for Name: events; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.events (seq, id, tenant_id, ts, graph_id, kind, payload, checksum, created_at) FROM stdin;
\.


--
-- Data for Name: graph_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.graph_version (tenant_id, graph_id, version, reason, updated_at) FROM stdin;
\.


--
-- Data for Name: ingest_dedup; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.ingest_dedup (tenant_id, graph_id, packet_hash, raw_id, node_count, created_at) FROM stdin;
\.


--
-- Data for Name: job_events; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.job_events (seq, job_id, ts, kind, payload) FROM stdin;
\.


--
-- Data for Name: jobs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.jobs (job_id, tenant_id, graph_id, kind, payload_json, status, error_message, created_at, updated_at, started_at, completed_at) FROM stdin;
\.


--
-- Data for Name: nodes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.nodes (node_id, tenant_id, graph_id, kind, vector_hash, raw_id, block_id, anchor_json, v_native, opp_signature, residual, level, touch_count, last_access, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: raw_refs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.raw_refs (id, tenant_id, sha256, uri, mime_type, size_bytes, graph_id, created_at) FROM stdin;
\.


--
-- Data for Name: schema_migrations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schema_migrations (version, applied_at, checksum) FROM stdin;
1	2026-01-17 14:34:44.679885	701b63db26c71c394de94c953c586409f80be18252946315af7efc433711f445
2	2026-01-17 14:34:44.92424	3c03c231af00eb165da82ed79228e0766646bf64b2b3dfdfccecd54969bbb74e
\.


--
-- Data for Name: snapshots; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.snapshots (id, tenant_id, graph_id, graph_version, graph_hash, node_count, metadata, created_at) FROM stdin;
\.


--
-- Name: events_seq_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.events_seq_seq', 1, false);


--
-- Name: job_events_seq_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.job_events_seq_seq', 1, false);


--
-- Name: edges edges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.edges
    ADD CONSTRAINT edges_pkey PRIMARY KEY (edge_id);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (seq);


--
-- Name: graph_version graph_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.graph_version
    ADD CONSTRAINT graph_version_pkey PRIMARY KEY (tenant_id, graph_id);


--
-- Name: ingest_dedup ingest_dedup_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingest_dedup
    ADD CONSTRAINT ingest_dedup_pkey PRIMARY KEY (tenant_id, graph_id, packet_hash);


--
-- Name: job_events job_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_events
    ADD CONSTRAINT job_events_pkey PRIMARY KEY (seq);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (job_id);


--
-- Name: nodes nodes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nodes
    ADD CONSTRAINT nodes_pkey PRIMARY KEY (node_id);


--
-- Name: raw_refs raw_refs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_refs
    ADD CONSTRAINT raw_refs_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: snapshots snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.snapshots
    ADD CONSTRAINT snapshots_pkey PRIMARY KEY (id);


--
-- Name: edges uq_edges_tenant_graph_src_dst_kind; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.edges
    ADD CONSTRAINT uq_edges_tenant_graph_src_dst_kind UNIQUE (tenant_id, graph_id, src_node_id, dst_node_id, kind);


--
-- Name: events uq_events_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT uq_events_id UNIQUE (id);


--
-- Name: job_events uq_job_events_job_id_seq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_events
    ADD CONSTRAINT uq_job_events_job_id_seq UNIQUE (job_id, seq);


--
-- Name: nodes uq_nodes_tenant_graph_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nodes
    ADD CONSTRAINT uq_nodes_tenant_graph_hash UNIQUE (tenant_id, graph_id, vector_hash);


--
-- Name: raw_refs uq_raw_refs_tenant_sha256; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_refs
    ADD CONSTRAINT uq_raw_refs_tenant_sha256 UNIQUE (tenant_id, sha256);


--
-- Name: idx_edges_child; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_edges_child ON public.edges USING btree (tenant_id, graph_id, dst_node_id, kind);


--
-- Name: idx_edges_parent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_edges_parent ON public.edges USING btree (tenant_id, graph_id, src_node_id, kind);


--
-- Name: idx_edges_tenant_graph; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_edges_tenant_graph ON public.edges USING btree (tenant_id, graph_id);


--
-- Name: idx_events_kind; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_kind ON public.events USING btree (kind);


--
-- Name: idx_events_tenant_graph_seq; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_tenant_graph_seq ON public.events USING btree (tenant_id, graph_id, seq);


--
-- Name: idx_events_ts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_ts ON public.events USING btree (ts DESC);


--
-- Name: idx_ingest_dedup_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ingest_dedup_created ON public.ingest_dedup USING btree (created_at DESC);


--
-- Name: idx_job_events_job_id_seq; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_events_job_id_seq ON public.job_events USING btree (job_id, seq);


--
-- Name: idx_job_events_ts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_events_ts ON public.job_events USING btree (ts);


--
-- Name: idx_jobs_graph; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_jobs_graph ON public.jobs USING btree (tenant_id, graph_id);


--
-- Name: idx_jobs_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_jobs_tenant_status ON public.jobs USING btree (tenant_id, status, created_at);


--
-- Name: idx_jobs_tenant_status_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_jobs_tenant_status_created ON public.jobs USING btree (tenant_id, status, created_at);


--
-- Name: idx_nodes_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nodes_created ON public.nodes USING btree (tenant_id, graph_id, created_at, node_id);


--
-- Name: idx_nodes_level; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nodes_level ON public.nodes USING btree (tenant_id, graph_id, level);


--
-- Name: idx_nodes_tenant_graph; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nodes_tenant_graph ON public.nodes USING btree (tenant_id, graph_id);


--
-- Name: idx_raw_refs_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_raw_refs_created ON public.raw_refs USING btree (created_at DESC);


--
-- Name: idx_raw_refs_tenant_graph; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_raw_refs_tenant_graph ON public.raw_refs USING btree (tenant_id, graph_id);


--
-- Name: idx_snapshots_tenant_graph; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_snapshots_tenant_graph ON public.snapshots USING btree (tenant_id, graph_id, created_at DESC);


--
-- Name: idx_snapshots_version; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_snapshots_version ON public.snapshots USING btree (graph_version);


--
-- Name: job_events job_events_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_events
    ADD CONSTRAINT job_events_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(job_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict uKXwE4QOVTRbb1xaBaGUUjuAhsVnrzoG2SLV7V2wbkjYsXxex7WywGoO27jJ8FG

