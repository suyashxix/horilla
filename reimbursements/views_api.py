from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Reimbursement
from .serializers import ReimbursementSerializer
from .ocr_utils import parse_invoice

class ReimbursementUploadAPI(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        serializer = ReimbursementSerializer(data=request.data)
        if serializer.is_valid():
            reimbursement = serializer.save()
            amount, vendor = parse_invoice(reimbursement.image.path)
            reimbursement.amount = amount
            reimbursement.vendor = vendor
            reimbursement.save()
            return Response(ReimbursementSerializer(reimbursement).data, status=201)
        return Response(serializer.errors, status=400)
