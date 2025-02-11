from __future__ import division, print_function
import unittest

import numpy as np
import pytest

from smqtk_descriptors.impls.descriptor_element.memory import \
    DescriptorMemoryElement
from smqtk_relevancy.impls.relevancy_index.libsvm_hik import LibSvmHikRelevancyIndex
from smqtk_core.configuration import configuration_test_helper

from typing import List


@pytest.mark.skipif(not LibSvmHikRelevancyIndex.is_usable(),
                    reason="LibSvmHikRelevancyIndex does not report as "
                           "usable.")
class TestIqrSvmHik (unittest.TestCase):

    d0: DescriptorMemoryElement
    d1: DescriptorMemoryElement
    d2: DescriptorMemoryElement
    d3: DescriptorMemoryElement
    d4: DescriptorMemoryElement
    d5: DescriptorMemoryElement
    d6: DescriptorMemoryElement
    index_descriptors: List[DescriptorMemoryElement]
    q_pos: DescriptorMemoryElement
    q_neg: DescriptorMemoryElement

    @classmethod
    def setUpClass(cls) -> None:
        # Don't need to clear cache because we're setting the vectors here
        cls.d0 = DescriptorMemoryElement('index', 0)
        cls.d0.set_vector(np.array([1, 0, 0, 0, 0], float))
        cls.d1 = DescriptorMemoryElement('index', 1)
        cls.d1.set_vector(np.array([0, 1, 0, 0, 0], float))
        cls.d2 = DescriptorMemoryElement('index', 2)
        cls.d2.set_vector(np.array([0, 0, 1, 0, 0], float))
        cls.d3 = DescriptorMemoryElement('index', 3)
        cls.d3.set_vector(np.array([0, 0, 0, 1, 0], float))
        cls.d4 = DescriptorMemoryElement('index', 4)
        cls.d4.set_vector(np.array([0, 0, 0, 0, 1], float))
        cls.d5 = DescriptorMemoryElement('index', 5)
        cls.d5.set_vector(np.array([0.5, 0, 0.5, 0, 0], float))
        cls.d6 = DescriptorMemoryElement('index', 6)
        cls.d6.set_vector(np.array([.2, .2, .2, .2, .2], float))
        cls.index_descriptors = [cls.d0, cls.d1, cls.d2, cls.d3, cls.d4,
                                 cls.d5, cls.d6]

        cls.q_pos = DescriptorMemoryElement('query', 0)
        cls.q_pos.set_vector(np.array([.75, .25, 0, 0, 0], float))
        cls.q_neg = DescriptorMemoryElement('query', 1)
        cls.q_neg.set_vector(np.array([0,   0,   0, .5, .5], float))

    def test_configuration(self) -> None:
        inst = LibSvmHikRelevancyIndex(
            descr_cache_filepath='foobar.thing',
            autoneg_select_ratio=89,
            multiprocess_fetch=True,
            cores=1
        )
        for i in configuration_test_helper(inst):  # type: LibSvmHikRelevancyIndex
            assert i.descr_cache_fp == 'foobar.thing'
            assert i.autoneg_select_ratio == 89
            assert i.multiprocess_fetch is True
            assert i.cores == 1

    def test_rank_no_neg(self) -> None:
        iqr_index = LibSvmHikRelevancyIndex()
        iqr_index.build_index(self.index_descriptors)
        # index should auto-select some negative examples, thus not raising
        # an exception.
        iqr_index.rank([self.q_pos], [])

    def test_rank_no_pos(self) -> None:
        iqr_index = LibSvmHikRelevancyIndex()
        iqr_index.build_index(self.index_descriptors)
        self.assertRaises(ValueError, iqr_index.rank, [], [self.q_neg])

    def test_rank_no_input(self) -> None:
        iqr_index = LibSvmHikRelevancyIndex()
        iqr_index.build_index(self.index_descriptors)
        self.assertRaises(ValueError, iqr_index.rank, [], [])

    def test_count(self) -> None:
        iqr_index = LibSvmHikRelevancyIndex()
        self.assertEqual(iqr_index.count(), 0)
        iqr_index.build_index(self.index_descriptors)
        self.assertEqual(iqr_index.count(), 7)

    def test_simple_iqr_scenario(self) -> None:
        # Make some descriptors;
        # Pick some from created set that are close to each other and use as
        #   positive query, picking some other random descriptors as
        #   negative examples.
        # Rank index based on chosen pos/neg
        # Check that positive choices are at the top of the ranking (closest
        #   to 0) and negative choices are closest to the bottom.
        iqr_index = LibSvmHikRelevancyIndex()
        iqr_index.build_index(self.index_descriptors)

        rank = iqr_index.rank([self.q_pos], [self.q_neg])
        rank_ordered = sorted(rank.items(), key=lambda e: e[1],
                              reverse=True)

        print("rank_ordered:")
        for i, r in enumerate(rank_ordered):
            print("..{}: {}".format(i, r))

        # Check expected ordering
        # 0-5-1-2-6-3-4
        # - 2 should end up coming before 6, because 6 has more intersection
        #   with the negative example.
        assert rank_ordered[0][0] == self.d0
        assert rank_ordered[1][0] == self.d5
        assert rank_ordered[2][0] == self.d1
        # Results show that d2 and d6 have the same rank, so their position
        # in interchangeable.
        assert rank_ordered[3][0] in (self.d2, self.d6)
        assert rank_ordered[4][0] in (self.d2, self.d6)
        assert rank_ordered[3][0] != rank_ordered[4][0]
        # d3 and d4 evaluate to the same rank based on query (no
        # intersection with positive, equal intersection with negative).
        assert rank_ordered[5][0] in (self.d3, self.d4)
        assert rank_ordered[6][0] in (self.d3, self.d4)
        assert rank_ordered[5][0] != rank_ordered[6][0]
