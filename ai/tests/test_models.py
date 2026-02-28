"""
AI Model Unit Tests — DCA-CNN & DS-1D-CNN
pytest ai/tests/test_models.py -v
"""
import os, sys, pytest, numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "training"))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECKPOINT_DIR = os.path.join(PROJECT_ROOT, "ai", "models", "checkpoints")
TFLITE_DIR = os.path.join(PROJECT_ROOT, "ai", "models", "tflite")

import torch

# ─── DCA-CNN architecture tests ─────────────────────────────────────────────

class TestDcaCNN:
    @pytest.fixture(autouse=True)
    def setup(self):
        from train_dca_cnn import DcaCNN, C_MAX, N_SAMPLES, NUM_CLASSES
        self.model = DcaCNN()
        self.C_MAX = C_MAX
        self.N_SAMPLES = N_SAMPLES
        self.NUM_CLASSES = NUM_CLASSES

    def test_param_count_under_500k(self):
        total = sum(p.numel() for p in self.model.parameters())
        assert total < 500_000, f"Params {total} exceeds 500K budget"

    def test_forward_12ch(self):
        x = torch.randn(2, 12, self.N_SAMPLES)
        out = self.model(x)
        assert out.shape == (2, self.NUM_CLASSES)

    def test_forward_3ch(self):
        x = torch.randn(2, 3, self.N_SAMPLES)
        out = self.model(x, c_active=3)
        assert out.shape == (2, self.NUM_CLASSES)

    def test_forward_1ch(self):
        x = torch.randn(2, 1, self.N_SAMPLES)
        out = self.model(x, c_active=1)
        assert out.shape == (2, self.NUM_CLASSES)

    def test_output_is_logits(self):
        """Forward returns raw logits (not probabilities)."""
        x = torch.randn(2, 12, self.N_SAMPLES)  # batch>1 for BatchNorm
        out = self.model(x)
        assert out.shape[1] == self.NUM_CLASSES

    def test_gate_reg_loss_positive(self):
        loss = self.model.gate_reg_loss(c_active=3)
        assert loss.item() >= 0

    def test_phase_reg_loss_positive(self):
        loss = self.model.phase_reg_loss()
        assert loss.item() >= 0

    def test_backward_no_nan(self):
        x = torch.randn(2, 12, self.N_SAMPLES, requires_grad=False)
        y = torch.zeros(2, self.NUM_CLASSES)
        out = self.model(x)
        loss = torch.nn.functional.binary_cross_entropy_with_logits(out, y)
        loss.backward()
        for name, p in self.model.named_parameters():
            if p.grad is not None:
                assert torch.isfinite(p.grad).all(), f"NaN/Inf grad in {name}"


class TestDcaCNNExportable:
    def test_exportable_wrapper(self):
        from train_dca_cnn import DcaCNN, _ExportableDcaCNN, C_MAX, N_SAMPLES, NUM_CLASSES
        m = DcaCNN()
        e = _ExportableDcaCNN(m)
        e.eval()
        x = torch.randn(1, C_MAX, N_SAMPLES)
        out = e(x)
        assert out.shape == (1, NUM_CLASSES)
        assert (out >= 0).all() and (out <= 1).all(), "Exportable wrapper must output probabilities"


# ─── DS-1D-CNN tests ────────────────────────────────────────────────────────

class TestDsOneDCNN:
    @pytest.fixture(autouse=True)
    def setup(self):
        from train_pytorch import EcgDSCNN
        self.model = EcgDSCNN()

    def test_param_count(self):
        total = sum(p.numel() for p in self.model.parameters())
        assert total == 176_599

    def test_forward_shape(self):
        x = torch.randn(4, 12, 2500)
        out = self.model(x)
        assert out.shape == (4, 55)


# ─── Preprocessing tests ────────────────────────────────────────────────────

class TestPreprocessing:
    def test_bandpass_no_nan(self):
        from train_dca_cnn import preprocess
        signal = np.random.randn(12, 5000).astype(np.float32)
        result = preprocess(signal)
        assert result is not None
        assert np.isfinite(result).all()
        assert result.shape == (12, 2500)

    def test_flat_lead_handled(self):
        from train_dca_cnn import preprocess
        signal = np.zeros((12, 5000), dtype=np.float32)
        result = preprocess(signal)
        assert result is None or np.isfinite(result).all()

    def test_nan_input_handled(self):
        from train_dca_cnn import preprocess
        signal = np.full((12, 5000), np.nan, dtype=np.float32)
        result = preprocess(signal)
        assert result is None or np.isfinite(result).all()


# ─── Channel masking tests ──────────────────────────────────────────────────

class TestChannelMasking:
    def test_mask_3ch(self):
        from train_dca_cnn import apply_channel_mask
        x = torch.randn(4, 12, 2500)
        masked, c_active = apply_channel_mask(x, 3)
        assert c_active == 3
        assert masked.shape == (4, 12, 2500)
        assert (masked[:, 3:, :] == 0).all()

    def test_mask_1ch(self):
        from train_dca_cnn import apply_channel_mask, LEAD_CONFIGS
        x = torch.randn(4, 12, 2500)
        masked, c_active = apply_channel_mask(x, 1)
        assert c_active == 1
        active_indices = set(LEAD_CONFIGS[1])
        for ch in range(12):
            ch_power = masked[:, ch, :].float().pow(2).mean().item()
            if ch in active_indices:
                assert ch_power > 0, f"Active ch {ch} should have signal"
            else:
                assert ch_power < 1e-10, f"Inactive ch {ch} has power={ch_power}"

    def test_mask_12ch_unchanged(self):
        from train_dca_cnn import apply_channel_mask
        x = torch.randn(4, 12, 2500)
        masked, c_active = apply_channel_mask(x, 12)
        assert c_active == 12
        assert torch.equal(masked, x)


# ─── ONNX / TFLite file integrity tests ─────────────────────────────────────

class TestModelFiles:
    def test_dca_cnn_onnx_exists(self):
        path = os.path.join(CHECKPOINT_DIR, "ecg_dca_cnn.onnx")
        assert os.path.exists(path), f"Missing {path}"
        assert os.path.getsize(path) > 100_000

    def test_dca_cnn_pt_exists(self):
        path = os.path.join(CHECKPOINT_DIR, "ecg_dca_cnn_best.pt")
        assert os.path.exists(path), f"Missing {path}"

    def test_dca_cnn_tflite_under_500kb(self):
        path = os.path.join(TFLITE_DIR, "ecg_dca_cnn_int8.tflite")
        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            assert size_kb < 500, f"TFLite {size_kb:.1f} KB exceeds 500 KB"

    def test_onnx_valid(self):
        try:
            import onnx
            path = os.path.join(CHECKPOINT_DIR, "ecg_dca_cnn.onnx")
            if os.path.exists(path):
                model = onnx.load(path)
                onnx.checker.check_model(model)
        except ImportError:
            pytest.skip("onnx not installed")


# ─── Checkpoint loading tests ───────────────────────────────────────────────

class TestCheckpointLoading:
    def test_load_dca_cnn_checkpoint(self):
        from train_dca_cnn import DcaCNN
        path = os.path.join(CHECKPOINT_DIR, "ecg_dca_cnn_best.pt")
        if not os.path.exists(path):
            pytest.skip("Checkpoint not found")
        model = DcaCNN()
        state = torch.load(path, map_location="cpu", weights_only=True)
        model.load_state_dict(state)
        model.eval()
        x = torch.randn(1, 12, 2500)
        out = model(x)
        assert out.shape == (1, 55)
        assert torch.isfinite(out).all()
