"""Stage-8 Test: No Chunking, No ML.

Proves query is FAIM-native:
- query_flow must not import chunking modules
- query_flow uses EvidenceBlock only
- No sentence-transformers imports
"""

import inspect
import unittest


class TestNoChunking(unittest.TestCase):
    """Test no chunking in query path."""

    def test_query_flow_no_chunking_import(self):
        """query_flow.py must not import chunking."""
        import orchestration.query_flow as qf

        source = inspect.getsource(qf)

        self.assertNotIn("from chunking", source)
        self.assertNotIn("import chunking", source)
        self.assertNotIn("split_text", source)

    def test_query_engine_no_chunking_import(self):
        """query_engine.py must not import chunking."""
        import core.query.query_engine as qe

        source = inspect.getsource(qe)

        self.assertNotIn("chunking", source.lower())
        self.assertNotIn("chunk_", source.lower())


class TestNoMLModels(unittest.TestCase):
    """Test no ML models in query path."""

    def test_query_flow_no_sentence_transformers(self):
        """query_flow.py must not use sentence-transformers."""
        import orchestration.query_flow as qf

        source = inspect.getsource(qf)

        self.assertNotIn("sentence_transformers", source)
        self.assertNotIn("SentenceTransformer", source)
        self.assertNotIn("transformers", source)

    def test_query_engine_no_sentence_transformers(self):
        """query_engine.py must not use sentence-transformers."""
        import core.query.query_engine as qe

        source = inspect.getsource(qe)

        self.assertNotIn("sentence_transformers", source)
        self.assertNotIn("SentenceTransformer", source)
        self.assertNotIn("transformers", source)

    def test_vectorizer_is_hashed_ngram(self):
        """Encoding uses hashed n-grams, not ML."""
        import encoding.text_vectorizer as vec

        source = inspect.getsource(vec)

        # Should use ngram hashing
        self.assertIn("ngram", source.lower())
        # Should NOT use sentence transformers
        self.assertNotIn("SentenceTransformer", source)


class TestUsesEvidenceBlocks(unittest.TestCase):
    """Test query uses EvidenceBlocks."""

    def test_vectorize_text_returns_object(self):
        """vectorize_text returns VectorizationResult object."""
        from encoding.text_vectorizer import VectorizationResult, vectorize_text

        result = vectorize_text("test query")

        # Result is an object with v_native, stats, opp_signature
        self.assertIsInstance(result, VectorizationResult)
        self.assertEqual(len(result.v_native), 256)
        self.assertIsInstance(result.stats, dict)
        self.assertIsInstance(result.opp_signature, dict)


if __name__ == "__main__":
    unittest.main()
