import unittest
from unittest.mock import patch

import mincer_package


class AmdGpuDetectionTests(unittest.TestCase):
    def test_detects_amd_display_controllers_without_rocm_host_tools(self):
        pci_devices = "\n".join(
            [
                "21:00.0 PCI bridge [0604]: Advanced Micro Devices [1002:14a0]",
                "23:00.0 Display controller [0380]: AMD/ATI Arcturus GL-XL "
                "[Instinct MI100] [1002:738c] (rev 01)",
                "83:00.0 Display controller [0380]: AMD/ATI Arcturus GL-XL "
                "[Instinct MI100] [1002:738c] (rev 01)",
                "00:02.0 VGA compatible controller [0300]: Matrox [102b:0532]",
            ]
        )
        with patch.object(mincer_package.subprocess, "call", return_value=1), patch.object(
            mincer_package.subprocess,
            "check_output",
            return_value=pci_devices,
        ):
            gpus = mincer_package.detect_gpus()

        self.assertEqual(len(gpus), 2)
        self.assertEqual([gpu["type"] for gpu in gpus], ["AMD GPU", "AMD GPU"])
        self.assertEqual(
            [gpu["name"] for gpu in gpus],
            [
                "23:00.0: AMD/ATI Arcturus GL-XL [Instinct MI100]",
                "83:00.0: AMD/ATI Arcturus GL-XL [Instinct MI100]",
            ],
        )


if __name__ == "__main__":
    unittest.main()
