from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    phone_number = fields.Char(
        string='Phone Number',
        related='partner_id.phone',
        readonly=True,
    )

    meal_type = fields.Selection(
        [
            ('breakfast', 'إفطار'),
            ('lunch', 'غداء'),
            ('dinner', 'عشاء'),
        ],
        string='الوجبة',
    )

    carcass_type = fields.Selection(
        [
            ('harri', 'حري'),
            ('najdi', 'نجدي'),
            ('naimi', 'نعيمي'),
            ('goat', 'تيس'),
        ],
        string='نوع الذبيحة',
    )


    carcass_count = fields.Float(
        string='عدد الذبائح',
        default=1.0,
        digits=(16, 2),
    )


    cooking_style = fields.Selection(
        [
            ('mandi', 'مندي'),
            ('mathbi', 'مظبي'),
            ('hanith', 'حنيذ'),
            ('kabsa', 'كبسة'),
        ],
        string='نوع الطبخ',
    )

    cutting_type = fields.Selection(
        [
            ('quarters', 'أرباع'),
            ('halves', 'أنصاف'),
            ('whole', 'كامل'),
        ],
        string='التفصيل',
    )

    plate_type = fields.Selection(
        [
            ('customer', 'صحون العميل'),
            ('restaurant', 'صحون المطعم'),
        ],
        string='نوع الصحون',
    )

    plate_count = fields.Integer(
        string='عدد الصحون',
        default=1,
    )

    order_date = fields.Datetime(
        string='Order Date',
        default=fields.Datetime.now,
        copy=False,
    )

    carcass_number = fields.Char(
        string='رقم الذبيحة',
        placeholder='بدون رقم',
    )

    delivery_date = fields.Datetime(
        string='تاريخ التوصيل',
    )

    order_notes = fields.Text(
        string='ملاحظات',
        placeholder='أضف ملاحظاتك هنا...',
    )

    delivery_type = fields.Selection(
        [
            ('pickup', 'بدون توصيل'),
            ('delivery', 'توصيل'),
        ],
        string='التوصيل',
        default='pickup',
    )


    # Constraints
    @api.constrains('plate_count')
    def _check_plate_count(self):
        for order in self:
            if order.plate_count < 0:
                raise ValidationError(
                    'عدد الصحون لا يمكن أن يكون رقماً سالباً.'
                )

    @api.constrains('carcass_count')
    def _check_carcass_count(self):
        for order in self:
            if order.carcass_count < 0:
                raise ValidationError(
                    'عدد الذبائح لا يمكن أن يكون رقماً سالباً.'
                )
