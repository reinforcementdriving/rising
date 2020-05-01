from typing import Sequence, Mapping, Hashable, Union, Callable, Tuple

import torch
from rising.transforms.abstract import AbstractTransform
from rising.transforms.functional.utility import seg_to_box, box_to_seg, instance_to_semantic, pop_keys, filter_keys

__all__ = ["DoNothing", "SegToBox", "BoxToSeg", "InstanceToSemantic", "PopKeys", "FilterKeys"]


class DoNothing(AbstractTransform):
    """Transform that returns the input as is"""

    def __init__(self, grad: bool = False, **kwargs):
        """
        Args:
            grad: enable gradient computation inside transformation
            **kwargs: keyword arguments passed to superclass
        """
        super().__init__(grad=grad, **kwargs)

    def forward(self, **data) -> dict:
        """
        Forward input

        Args:
            data: input dict

        Returns:
            input dict
        """
        return data


class SegToBox(AbstractTransform):
    """Convert instance segmentation to bounding boxes"""

    def __init__(self, keys: Mapping[Hashable, Hashable], grad: bool = False, **kwargs):
        """
        Args:
            keys: the key specifies which item to use as segmentation and the
                item specifies where the save the bounding boxes
            grad: enable gradient computation inside transformation
        """
        super().__init__(grad=grad, **kwargs)
        self.keys = keys

    def forward(self, **data) -> dict:
        """

        Args:
            **data: input data

        Returns:
            transformed data

        """

        for source, target in self.keys.items():
            data[target] = [seg_to_box(s, s.ndim - 2) for s in data[source].split(1)]
        return data


class BoxToSeg(AbstractTransform):
    """Convert bounding boxes to instance segmentation"""

    def __init__(self, keys: Mapping[Hashable, Hashable], shape: Sequence[int],
                 dtype: torch.dtype, device: Union[torch.device, str],
                 grad: bool = False, **kwargs):
        """
        keys: the key specifies which item to use as the bounding boxes and
            the item specifies where the save the bounding boxes
        shape: spatial shape of output tensor (batchsize is derived from
            bounding boxes and has one channel)
        dtype: dtype of segmentation
        device: device of segmentation
        grad: enable gradient computation inside transformation
        **kwargs: Additional keyword arguments forwarded to the Base Class
        """
        super().__init__(grad=grad, **kwargs)
        self.keys = keys
        self.seg_shape = shape
        self.seg_dtype = dtype
        self.seg_device = device

    def forward(self, **data) -> dict:
        """
        Forward input

        Args:
            **data: input data

        Returns:
            transformed data
        """
        for source, target in self.keys.items():
            out = torch.zeros((len(data[source]), 1, *self.seg_shape), dtype=self.seg_dtype,
                              device=self.seg_device)
            for b in range(len(data[source])):
                box_to_seg(data[source][b], out=out[b])
            data[target] = out
        return data


class InstanceToSemantic(AbstractTransform):
    """Convert an instance segmentation to a semantic segmentation"""

    def __init__(self, keys: Mapping[str, str], cls_key: Hashable, grad: bool = False, **kwargs):
        """
        Args:
            keys: the key specifies which item to use as instance segmentation
                and the item specifies where the save the semantic segmentation
            cls_key: key where the class mapping is saved. Mapping needs to
                be a Sequence{Sequence[int]].
            grad: enable gradient computation inside transformation
        """
        super().__init__(grad=grad, **kwargs)
        self.cls_key = cls_key
        self.keys = keys

    def forward(self, **data) -> dict:
        """
        Forward input

        Args:
            **data: input data

        Returns:
            transformed data

        """
        for source, target in self.keys.items():
            data[target] = torch.cat([instance_to_semantic(data, mapping)
                                      for data, mapping in zip(data[source].split(1), data[self.cls_key])])
        return data


class PopKeys(AbstractTransform):
    """Pops keys from a given data dict"""

    def __init__(self, keys: Union[Callable, Sequence], return_popped: bool = False):
        """
        Args:
            keys : if callable it must return a boolean for each key
                indicating whether it should be popped from the dict.
                if sequence of strings, the strings shall be the keys to be
                popped
            return_popped: whether to also return the popped values
                (default: False)

        """
        super().__init__(grad=False)
        self.keys = keys
        self.return_popped = return_popped

    def forward(self, **data) -> Union[dict, Tuple[dict, dict]]:
        return pop_keys(data=data, keys=self.keys, return_popped=self.return_popped)


class FilterKeys(AbstractTransform):
    """Filters keys from a given data dict"""

    def __init__(self, keys: Union[Callable, Sequence], return_popped: bool = False):
        """
        Args:
            keys: if callable it must return a boolean for each key
                indicating whether it should be retained in the dict.
                if sequence of strings, the strings shall be the keys to be
                retained
            return_popped: whether to also return the popped values
                (default: False)

        """
        super().__init__(grad=False)
        self.keys = keys
        self.return_popped = return_popped

    def forward(self, **data) -> Union[dict, Tuple[dict, dict]]:
        return filter_keys(data=data, keys=self.keys, return_popped=self.return_popped)
