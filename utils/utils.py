import torch

def normalize_tensor(input_tens):
    i_max = input_tens.max()
    i_min = input_tens.min()
    input_tens = (input_tens-i_min)/(i_max-i_min)
    return input_tens

def dice_loss(prediction, target):
    # Dice loss
    prediction = prediction[:, 0].contiguous().view(-1)
    target = target[:, 0].contiguous().view(-1)
    intersection = (prediction * target).sum()
    return 1 - ((2. * intersection + 1) / (prediction.sum() + target.sum() + 1))

def total_variation(images):
    """
    Edited from tensorflow implementation

    Calculate and return the total variation for one or more images.

    The total variation is the sum of the absolute differences for neighboring
    pixel-values in the input images. This measures how much noise is in the
    images.

    This implements the anisotropic 2-D version of the formula described here:
    https://en.wikipedia.org/wiki/Total_variation_denoising

    Args:
        images: 3-D Tensor of shape `[batch, height, width]`.
    Returns:
        The total variation of `images`.

        return a scalar float with the total variation for
        that image.
    """

    # The input is a single image with shape [batch, height, width].

    # Calculate the difference of neighboring pixel-values.
    # The images are shifted one pixel along the height and width by slicing.
    pixel_dif1 = images[:, 1:, :] - images[:, :-1, :]
    pixel_dif2 = images[:, :, 1:] - images[:, :, :-1]

    # Sum for all axis. (None is an alias for all axis.)

    # Calculate the total variation by taking the absolute value of the
    # pixel-differences and summing over the appropriate axis.
    tot_var = (
        torch.sum(torch.abs(pixel_dif1)) +
        torch.sum(torch.abs(pixel_dif2)))

    return tot_var