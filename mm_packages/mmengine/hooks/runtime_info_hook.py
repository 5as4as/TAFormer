# Copyright (c) OpenMMLab. All rights reserved.
from typing import Dict, Optional, Union

from mmengine.registry import HOOKS
from mmengine.utils import get_git_hash
from mmengine.version import __version__
from .hook import Hook

DATA_BATCH = Optional[Union[dict, tuple, list]]


@HOOKS.register_module()
class RuntimeInfoHook(Hook):
    """A hook that updates runtime information into message hub.

    E.g. ``epoch``, ``iter``, ``max_epochs``, and ``max_iters`` for the
    training state. Components that cannot access the runner can get runtime
    information through the message hub.
    """

    priority = 'VERY_HIGH'

    def before_run(self, runner) -> None:
        """Update metainfo.

        Args:
            runner (Runner): The runner of the training process.
        """
        metainfo = dict(
            cfg=runner.cfg.pretty_text,
            seed=runner.seed,
            experiment_name=runner.experiment_name,
            mmengine_version=__version__ + get_git_hash())
        runner.message_hub.update_info_dict(metainfo)

    def before_train(self, runner) -> None:
        """Update resumed training state.

        Args:
            runner (Runner): The runner of the training process.
        """
        runner.message_hub.update_info('epoch', runner.epoch)
        runner.message_hub.update_info('iter', runner.iter)
        runner.message_hub.update_info('max_epochs', runner.max_epochs)
        runner.message_hub.update_info('max_iters', runner.max_iters)
        if isinstance(runner.train_dataloader, list):
            if hasattr(runner.train_dataloader[0].dataset, 'metainfo'):
                runner.message_hub.update_info(
                    'dataset_meta', runner.train_dataloader[0].dataset.metainfo)
        else:
            if hasattr(runner.train_dataloader.dataset, 'metainfo'):
                runner.message_hub.update_info(
                    'dataset_meta', runner.train_dataloader.dataset.metainfo)

    def before_train_epoch(self, runner) -> None:
        """Update current epoch information before every epoch.

        Args:
            runner (Runner): The runner of the training process.
        """
        runner.message_hub.update_info('epoch', runner.epoch)

    def before_train_iter(self,
                          runner,
                          batch_idx: int,
                          data_batch: DATA_BATCH = None) -> None:
        """Update current iter and learning rate information before every
        iteration.

        Args:
            runner (Runner): The runner of the training process.
            batch_idx (int): The index of the current batch in the train loop.
            data_batch (Sequence[dict], optional): Data from dataloader.
                Defaults to None.
        """
        runner.message_hub.update_info('iter', runner.iter)
        lr_dict = runner.optim_wrapper.get_lr()
        assert isinstance(lr_dict, dict), (
            '`runner.optim_wrapper.get_lr()` should return a dict '
            'of learning rate when training with OptimWrapper(single '
            'optimizer) or OptimWrapperDict(multiple optimizer), '
            f'but got {type(lr_dict)} please check your optimizer '
            'constructor return an `OptimWrapper` or `OptimWrapperDict` '
            'instance')
        for name, lr in lr_dict.items():
            runner.message_hub.update_scalar(f'train/{name}', lr[0])

    def after_train_iter(self,
                         runner,
                         batch_idx: int,
                         data_batch: DATA_BATCH = None,
                         outputs: Optional[dict] = None) -> None:
        """Update ``log_vars`` in model outputs every iteration.

        Args:
            runner (Runner): The runner of the training process.
            batch_idx (int): The index of the current batch in the train loop.
            data_batch (Sequence[dict], optional): Data from dataloader.
                Defaults to None.
            outputs (dict, optional): Outputs from model. Defaults to None.
        """
        if outputs is not None:
            for key, value in outputs.items():
                runner.message_hub.update_scalar(f'train/{key}', value)

    def after_val_epoch(self,
                        runner,
                        metrics: Optional[Dict[str, float]] = None) -> None:
        """All subclasses should override this method, if they need any
        operations after each validation epoch.

        Args:
            runner (Runner): The runner of the validation process.
            metrics (Dict[str, float], optional): Evaluation results of all
                metrics on validation dataset. The keys are the names of the
                metrics, and the values are corresponding results.
        """
        if metrics is not None:
            for key, value in metrics.items():
                runner.message_hub.update_scalar(f'val/{key}', value)

    def after_test_epoch(self,
                         runner,
                         metrics: Optional[Dict[str, float]] = None) -> None:
        """All subclasses should override this method, if they need any
        operations after each test epoch.

        Args:
            runner (Runner): The runner of the testing process.
            metrics (Dict[str, float], optional): Evaluation results of all
                metrics on test dataset. The keys are the names of the
                metrics, and the values are corresponding results.
        """
        if metrics is not None:
            for key, value in metrics.items():
                runner.message_hub.update_scalar(f'test/{key}', value)
