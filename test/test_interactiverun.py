# Copyright 2018 Uber Technologies, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest
import warnings

import pytest
import torch

import horovod.torch as hvd

from horovod.common.util import gloo_built, mpi_built
from horovod.run import run


class InteractiveRunTests(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(InteractiveRunTests, self).__init__(*args, **kwargs)
        warnings.simplefilter('module')

    def test_happy_run(self):
        def fn(a, b, c, d):
            hvd.init()
            rank = hvd.rank()
            v = a + b + c + d
            res = hvd.allgather(torch.tensor([rank, v])).tolist()
            if rank == 0:
                return res
            elif rank == 1:
                return "ret_val_of_rank_1"
            else:
                return None

        assert gloo_built() or mpi_built()
        for use_gloo, use_mpi in [(True, False), (False, True)]:
            if use_mpi and not mpi_built():
                continue

            if use_gloo and not gloo_built():
                continue

            res1 = run(fn, (1, 20), {"c": 300, "d": 4000}, np=1, use_gloo=use_gloo, use_mpi=use_mpi)
            self.assertListEqual([[0, 4321]], res1)
            res2 = run(fn, (1, 20), {"c": 300, "d": 4000}, np=3, use_gloo=use_gloo, use_mpi=use_mpi)
            self.assertListEqual([[0, 4321, 1, 4321, 2, 4321],
                                  "ret_val_of_rank_1",
                                  None], res2)

    def test_failed_run(self):
        def fn():
            hvd.init()
            rank = hvd.rank()
            if rank == 1:
                raise RuntimeError()

        assert gloo_built() or mpi_built()

        if gloo_built():
            with pytest.raises(RuntimeError, match='Horovod detected that one or more processes exited'):
                run(fn, np=2, use_gloo=True)

        if mpi_built():
            with pytest.raises(RuntimeError, match='mpirun failed'):
                run(fn, np=2, use_mpi=True)
